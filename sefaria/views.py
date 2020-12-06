# -*- coding: utf-8 -*-
import io
import os
import zipfile
import json
import re
import bleach
from datetime import datetime, timedelta
from urllib.parse import urlparse
from collections import defaultdict
from random import choice
from webpack_loader import utils as webpack_utils

from django.utils.translation import ugettext as _
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.contrib.auth import authenticate
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.urls import resolve
from django.urls.exceptions import Resolver404
from rest_framework.decorators import api_view
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import sefaria.model as model
import sefaria.system.cache as scache
from sefaria.client.util import jsonResponse, subscribe_to_list, send_email
from sefaria.forms import SefariaNewUserForm, SefariaNewUserFormAPI
from sefaria.settings import MAINTENANCE_MESSAGE, USE_VARNISH, MULTISERVER_ENABLED, relative_to_abs_path, PARTNER_GROUP_EMAIL_PATTERN_LOOKUP_FILE, RTC_SERVER
from sefaria.model.user_profile import UserProfile, user_link
from sefaria.model.group import GroupSet
from sefaria.export import export_all as start_export_all
from sefaria.datatype.jagged_array import JaggedTextArray
# noinspection PyUnresolvedReferences
from sefaria.system.exceptions import InputError
from sefaria.system.database import db
from sefaria.system.decorators import catch_error_as_http
from sefaria.utils.hebrew import is_hebrew, strip_nikkud
from sefaria.utils.util import strip_tags
from sefaria.helper.text import make_versions_csv, get_library_stats, get_core_link_stats, dual_text_diff
from sefaria.clean import remove_old_counts
from sefaria.search import index_sheets_by_timestamp as search_index_sheets_by_timestamp
from sefaria.model import *
from sefaria.system.multiserver.coordinator import server_coordinator


if USE_VARNISH:
    from sefaria.system.varnish.wrapper import invalidate_index, invalidate_title, invalidate_ref, invalidate_counts, invalidate_all

import logging
logger = logging.getLogger(__name__)


def process_register_form(request, auth_method='session'):
    form = SefariaNewUserForm(request.POST) if auth_method == 'session' else SefariaNewUserFormAPI(request.POST)
    token_dict = None
    if form.is_valid():
        with transaction.atomic():
            new_user = form.save()
            user = authenticate(email=form.cleaned_data['email'],
                                password=form.cleaned_data['password1'])
            p = UserProfile(id=user.id)
            p.assign_slug()
            p.join_invited_groups()
            if hasattr(request, "interfaceLang"):
                p.settings["interface_language"] = request.interfaceLang

            p.save()
        if auth_method == 'session':
            auth_login(request, user)
        elif auth_method == 'jwt':
            token_dict = TokenObtainPairSerializer().validate({"username": form.cleaned_data['email'], "password": form.cleaned_data['password1']})
    return {
        k: v[0] if len(v) > 0 else str(v) for k, v in list(form.errors.items())
    }, token_dict, form


@api_view(["POST"])
def register_api(request):
    errors, token_dict, _ = process_register_form(request, auth_method='jwt')
    if len(errors) == 0:
        return jsonResponse(token_dict)

    return jsonResponse(errors)


def register(request):
    if request.user.is_authenticated:
        return redirect("login")

    next = request.GET.get('next', '')

    if request.method == 'POST':
        errors, _, form = process_register_form(request)
        if len(errors) == 0:
            if "noredirect" in request.POST:
                return HttpResponse("ok")
            elif "new?assignment=" in request.POST.get("next",""):
                next = request.POST.get("next", "")
                return HttpResponseRedirect(next)
            else:
                next = request.POST.get("next", "/")
                if "?" in next:
                    next += "&welcome=to-sefaria"
                else:
                    next += "?welcome=to-sefaria"
                return HttpResponseRedirect(next)
    else:
        if request.GET.get('educator', ''):
            form = SefariaNewUserForm(initial={'subscribe_educator': True})
        else:
            form = SefariaNewUserForm()

    return render(request, "registration/register.html", {'form': form, 'next': next})


def maintenance_message(request):
    resp = render(request,"static/maintenance.html",
                                {"message": MAINTENANCE_MESSAGE})
    resp.status_code = 503
    return resp


def accounts(request):
    return render(request,"registration/accounts.html",
                                {"createForm": UserCreationForm(),
                                "loginForm": AuthenticationForm()})


def subscribe(request, email):
    """
    API for subscribg is mailing lists, in `lists` url param.
    Currently active lists are:
    "Announcements_General", "Announcements_General_Hebrew", "Announcements_Edu", "Announcements_Edu_Hebrew"
    """
    lists = request.GET.get("lists", "")
    lists = lists.split("|")
    if len(lists) == 0:
        return jsonResponse({"error": "Please specifiy a list."})
    if subscribe_to_list(lists + ["Newsletter_Sign_Up"], email, direct_sign_up=True):
        return jsonResponse({"status": "ok"})
    else:
        return jsonResponse({"error": _("Sorry, there was an error.")})


def generate_feedback(request):

    data = json.loads(request.POST.get('json', {}))

    fb_type = data.get('type', None)
    refs = data.get('refs', None)
    url = data.get('url', None)
    versions = data.get('currVersions', None)
    uid = data.get('uid', None)
    from_email = data.get('email', None)
    msg = data.get('msg', None)

    if not from_email:
        from_email = model.user_profile.UserProfile(id=uid).email

    if fb_type == "content_issue":
        to_email = "corrections@sefaria.org"
        subject = "Correction from website - " + ' / '.join(refs)
        message_html = msg + "\n\n" + "refs: " + ' / '.join(refs) + "\n" + "versions: " + str(versions) + "\n\n" + "URL: " + url
    elif fb_type == "user_testing":
        to_email = "gabriel@sefaria.org"
        subject = "User Testing Sign Up"
        message_html = "Hi! I want to sign up for user testing!"
    else:
        to_email = "hello@sefaria.org"
        subject = "Feedback from website - " + fb_type.replace("_"," ")
        message_html = msg + "\n\n" + "URL: " + url

    try:
        send_email(subject, message_html, from_email, to_email)
        return jsonResponse({"status": "ok"})
    except:
        return jsonResponse({"error": _("Sorry, there was an error.")})


def data_js(request):
    """
    Javascript populating dynamic data like book lists, toc.
    """
    return render(request, "js/data.js", content_type="text/javascript")


def sefaria_js(request):
    """
    Packaged Sefaria.js.
    """
    data_js = render_to_string("js/data.js", context={}, request=request)
    webpack_files = webpack_utils.get_files('main', config="SEFARIA_JS")
    bundle_path = relative_to_abs_path('..' + webpack_files[0]["url"])
    with open(bundle_path, 'r') as file:
        sefaria_js=file.read()
    attrs = {
        "data_js": data_js,
        "sefaria_js": sefaria_js,
    }

    return render(request, "js/sefaria.js", attrs, content_type= "text/javascript")

def chavruta_js(request):
    """
    Javascript for chavruta [required to pass server attribute].
    """
    client_user = UserProfile(id=request.user.id)
    roulette = request.GET.get("roulette", "0")

    attrs = {
        "rtc_server": RTC_SERVER,
        "client_name": client_user.first_name + " " + client_user.last_name,
        "client_uid": client_user.id,
        "roulette": roulette
    }


    return render(request, "js/chavruta.js", attrs, content_type="text/javascript")



def linker_js(request, linker_version=None):
    """
    Javascript of Linker plugin.
    """
    CURRENT_LINKER_VERSION = "2"
    linker_version = linker_version or CURRENT_LINKER_VERSION
    linker_link = "js/linker.v" + linker_version + ".js"

    attrs = {
        "book_titles": json.dumps(model.library.citing_title_list("en")
                      + model.library.citing_title_list("he"))
    }

    return render(request, linker_link, attrs, content_type = "text/javascript")


def title_regex_api(request, titles):
    if request.method == "GET":
        cb = request.GET.get("callback", None)
        parentheses = bool(int(request.GET.get("parentheses", False)))
        titles = set(titles.split("|"))
        res = {}
        errors = []
        for title in titles:
            lang = "he" if is_hebrew(title) else "en"
            try:
                re_string = model.library.get_regex_string(title, lang, anchored=False, for_js=True, parentheses=parentheses)
                res[title] = re_string
            except (AttributeError, AssertionError) as e:
                # There are normal errors here, when a title matches a schema node, the chatter fills up the logs.
                # logger.warning(u"Library._build_ref_from_string() failed to create regex for: {}.  {}".format(title, e))
                errors.append("{} : {}".format(title, e))
        if len(errors):
            res["error"] = errors
        resp = jsonResponse(res, cb)
        return resp
    else:
        return jsonResponse({"error": "Unsupported HTTP method."})


def bundle_many_texts(refs, useTextFamily=False, as_sized_string=False, min_char=None, max_char=None):
    res = {}
    for tref in refs:
        try:
            oref = model.Ref(tref)
            lang = "he" if is_hebrew(tref) else "en"
            if useTextFamily:
                text_fam = model.TextFamily(oref, commentary=0, context=0, pad=False)
                he = text_fam.he
                en = text_fam.text
                res[tref] = {
                    'he': he,
                    'en': en,
                    'lang': lang,
                    'ref': oref.normal(),
                    'primary_category': text_fam.contents()['primary_category'],
                    'heRef': oref.he_normal(),
                    'url': oref.url()
                }
            else:
                he_tc = model.TextChunk(oref, "he")
                en_tc = model.TextChunk(oref, "en")
                if as_sized_string:
                    kwargs = {}
                    if min_char:
                        kwargs['min_char'] = min_char
                    if max_char:
                        kwargs['max_char'] = max_char
                    he_text = he_tc.as_sized_string(**kwargs)
                    en_text = en_tc.as_sized_string(**kwargs)
                else:
                    he = he_tc.text
                    en = en_tc.text
                    # these could be flattened on the client, if need be.
                    he_text = he if isinstance(he, str) else JaggedTextArray(he).flatten_to_string()
                    en_text = en if isinstance(en, str) else JaggedTextArray(en).flatten_to_string()

                res[tref] = {
                    'he': he_text,
                    'en': en_text,
                    'lang': lang,
                    'ref': oref.normal(),
                    'heRef': oref.he_normal(),
                    'url': oref.url()
                }
        except (InputError, ValueError, AttributeError, KeyError) as e:
            # referer = request.META.get("HTTP_REFERER", "unknown page")
            # This chatter fills up the logs.  todo: put in it's own file
            # logger.warning(u"Linker failed to parse {} from {} : {}".format(tref, referer, e))
            res[tref] = {"error": 1}
    return res

def bulktext_api(request, refs):
    """
    Used by the linker.
    :param request:
    :param refs:
    :return:
    """
    if request.method == "GET":
        cb = request.GET.get("callback", None)
        refs = set(refs.split("|"))
        g = lambda x: request.GET.get(x, None)
        min_char = int(g("minChar")) if g("minChar") else None
        max_char = int(g("maxChar")) if g("maxChar") else None
        res = bundle_many_texts(refs, g("useTextFamily"), g("asSizedString"), min_char, max_char)
        resp = jsonResponse(res, cb)
        return resp


@csrf_exempt
def linker_tracking_api(request):
    """
    API tracking hits on the linker and storing webpages from them.
    """
    if request.method != "POST":
        return jsonResponse({"error": "Method not implemented."})

    j = request.POST.get("json")
    if not j:
        return jsonResponse({"error": "Missing 'json' parameter in post data."})
    data = json.loads(j)

    status = WebPage.add_or_update_from_linker(data)

    return jsonResponse({"status": status})


def passages_api(request, refs):
    """
    Returns a dictionary, mapping the refs in the request to the sugya that they're a part of.

    :param request:
    :param refs:
    :return:
    """
    if request.method == "GET":
        response = {}
        cb = request.GET.get("callback", None)
        refs = set(refs.split("|"))

        # todo: Use PassageSet, so that it can be packaged as one query
        for tref in refs:
            try:
                oref = Ref(tref)
                p = Passage().load({"ref_list": oref.normal()})
                if p:
                    response[tref] = p.full_ref
                else:
                    response[tref] = oref.normal()
            except InputError:
                response[tref] = tref  # is this the best thing to do?  It passes junk along...

        resp = jsonResponse(response, cb)
        return resp


@login_required
def file_upload(request, resize_image=True):
    from PIL import Image
    from tempfile import NamedTemporaryFile
    from sefaria.s3 import HostedFile
    if request.method == "POST":
        MAX_FILE_MB = 2
        MAX_FILE_SIZE = MAX_FILE_MB * 1024 * 1024
        MAX_FILE_DIMENSIONS = (1048, 1048)
        uploaded_file = request.FILES['file']
        if uploaded_file.size > MAX_FILE_SIZE:
            return jsonResponse({"error": "Uploaded files must be smaller than %dMB." % MAX_FILE_MB})
        name, extension = os.path.splitext(uploaded_file.name)
        with NamedTemporaryFile(suffix=extension) as temp_uploaded_file:
            temp_uploaded_file.write(uploaded_file.read())

            with NamedTemporaryFile(suffix=extension) as temp_resized_file:
                image = Image.open(temp_uploaded_file)
                if resize_image:
                    image.thumbnail(MAX_FILE_DIMENSIONS, Image.ANTIALIAS)
                image.save(temp_resized_file, optimize=True, quality=70)

                name, extension = os.path.splitext(temp_resized_file.name)
                hosted_file = HostedFile(filepath=temp_resized_file.name, content_type=uploaded_file.content_type)
                try:
                    url = hosted_file.upload()
                    return jsonResponse({"status": "success", "url": url})
                except:
                    return jsonResponse({"error": "There was an error uploading your file."})
    else:
        return jsonResponse({"error": "Unsupported HTTP method."})


@staff_member_required
def reset_cache(request):
    model.library.rebuild()

    if MULTISERVER_ENABLED:
        server_coordinator.publish_event("library", "rebuild")

    if USE_VARNISH:
        invalidate_all()

    return HttpResponseRedirect("/?m=Cache-Reset")


@staff_member_required
def reset_index_cache_for_text(request, title):

    index = model.library.get_index(title)
    model.library.refresh_index_record_in_cache(index)
    model.library.reset_text_titles_cache()

    if MULTISERVER_ENABLED:
        server_coordinator.publish_event("library", "refresh_index_record_in_cache", [index.title])
    elif USE_VARNISH:
        invalidate_title(index.title)

    return HttpResponseRedirect("/%s?m=Cache-Reset" % model.Ref(title).url())


"""@staff_member_required
def view_cached_elem(request, title):
    return HttpResponse(get_template_cache('texts_list'), status=200)
"""

@staff_member_required
def reset_cached_api(request, apiurl):
    """
    This admin call gets the url of the original api that we wish to reset, backwards resolves that original function and gets its data back into cache
    :param request:
    :param apiurl:
    :return:
    """
    from undecorated import undecorated
    # from importlib import import_module
    try:
        match = resolve("/api/{}".format(apiurl))
        #mod = import_module(".".join(match.view_name.split(".")[:-1])) Dont actually need this, resolve gets us the func itself
        #func = mod.__getattribute__(match.func.func_name)

        if "django_cache" in match.func.__dict__:
            api_view = undecorated(match.func)
            redecorated_api_view = scache.django_cache(action="reset")(api_view)
            redecorated_api_view(request, *match.args, **match.kwargs)

            return HttpResponseRedirect("/api/{}".format(apiurl))
        else:
            raise Http404("API not in cache")

    except Resolver404 as re:
        logger.warn("Attempted to reset invalid url")
        raise Http404()
    except Exception as e:
        logger.warn("Unable to reset cache for {}".format(apiurl))
        raise Http404()


@staff_member_required
def reset_counts(request, title=None):
    if title:
        try:
            i = model.library.get_index(title)
        except:
            return HttpResponseRedirect("/dashboard?m=Unknown-Book")
        vs = model.VersionState(index=i)
        vs.refresh()

        return HttpResponseRedirect("/%s?m=Counts-Rebuilt" % model.Ref(i.title).url())
    else:
        model.refresh_all_states()

        if MULTISERVER_ENABLED:
            server_coordinator.publish_event("library", "rebuild_toc")

        return HttpResponseRedirect("/?m=Counts-Rebuilt")


@staff_member_required
def delete_orphaned_counts(request):
    remove_old_counts()
    scache.delete_template_cache("texts_dashboard")

    if MULTISERVER_ENABLED:
        server_coordinator.publish_event("scache", "delete_template_cache", ["texts_dashboard"])

    return HttpResponseRedirect("/dashboard?m=Orphaned-counts-deleted")


@staff_member_required
def rebuild_toc(request):
    model.library.rebuild_toc()

    if MULTISERVER_ENABLED:
        server_coordinator.publish_event("library", "rebuild_toc")

    return HttpResponseRedirect("/?m=TOC-Rebuilt")


@staff_member_required
def rebuild_auto_completer(request):
    library.build_full_auto_completer()
    library.build_ref_auto_completer()
    library.build_lexicon_auto_completers()
    library.build_cross_lexicon_auto_completer()

    if MULTISERVER_ENABLED:
        server_coordinator.publish_event("library", "build_full_auto_completer")
        server_coordinator.publish_event("library", "build_ref_auto_completer")
        server_coordinator.publish_event("library", "build_lexicon_auto_completers")
        server_coordinator.publish_event("library", "build_cross_lexicon_auto_completer")

    return HttpResponseRedirect("/?m=auto-completer-Rebuilt")


'''
# No usages found
@staff_member_required
def rebuild_counts_and_toc(request):
    model.refresh_all_states()
    return HttpResponseRedirect("/?m=Counts-&-TOC-Rebuilt")
'''


@staff_member_required
def reset_varnish(request, tref):
    if USE_VARNISH:
        oref = model.Ref(tref)
        if oref.is_book_level():
            invalidate_index(oref.index)
            invalidate_counts(oref.index)
        invalidate_ref(oref)
        return HttpResponseRedirect("/?m=Varnish-Reset-For-{}".format(oref.url()))
    return HttpResponseRedirect("/?m=Varnish-Not-Enabled")


@staff_member_required
def reset_ref(request, tref):
    """
    resets cache, versionstate, toc, varnish, & book TOC template
    :param tref:
    :return:
    """
    oref = model.Ref(tref)
    if oref.is_book_level():
        model.library.refresh_index_record_in_cache(oref.index)
        model.library.reset_text_titles_cache()
        vs = model.VersionState(index=oref.index)
        vs.refresh()
        model.library.update_index_in_toc(oref.index)

        if MULTISERVER_ENABLED:
            server_coordinator.publish_event("library", "refresh_index_record_in_cache", [oref.index.title])
            server_coordinator.publish_event("library", "update_index_in_toc", [oref.index.title])
        elif USE_VARNISH:
            invalidate_title(oref.index.title)

        return HttpResponseRedirect("/{}?m=Reset-Index".format(oref.url()))

    elif USE_VARNISH:
        invalidate_ref(oref)
        return HttpResponseRedirect("/{}?m=Reset-Ref".format(oref.url()))

    else:
        return HttpResponseRedirect("/?m=Nothing-to-Reset")


@staff_member_required
def rebuild_auto_links(request, title):
    from sefaria.helper.link import rebuild_links_for_title as rebuild
    rebuild(title, request.user.id)
    return HttpResponseRedirect("/?m=Automatic-Links-Rebuilt-on-%s" % title)


@staff_member_required
def rebuild_citation_links(request, title):
    from sefaria.helper.link import rebuild_links_from_text as rebuild
    rebuild(title, request.user.id)
    return HttpResponseRedirect("/?m=Citation-Links-Rebuilt-on-%s" % title)


@staff_member_required
def delete_citation_links(request, title):
    from sefaria.helper.link import delete_links_from_text
    delete_links_from_text(title, request.user.id)
    return HttpResponseRedirect("/?m=Citation-Links-Deleted-on-%s" % title)


@staff_member_required
def cache_stats(request):
    import resource
    from sefaria.utils.util import get_size
    from sefaria.model.user_profile import public_user_data_cache
    # from sefaria.sheets import last_updated
    resp = {
        'ref_cache_size': model.Ref.cache_size(),
        # 'ref_cache_bytes': model.Ref.cache_size_bytes(), # This pretty expensive, not sure if it should run on prod.
        'public_user_data_size': len(public_user_data_cache),
        'public_user_data_bytes': get_size(public_user_data_cache),
        # 'sheets_last_updated_size': len(last_updated),
        # 'sheets_last_updated_bytes': get_size(last_updated),
        'memory usage': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    }
    return jsonResponse(resp)


@staff_member_required
def cache_dump(request):
    resp = {
        'ref_cache_dump': model.Ref.cache_dump()
    }
    return jsonResponse(resp)


@staff_member_required
def export_all(request):
    start = datetime.now()
    try:
        start_export_all()
        resp = {"status": "ok"}
    except Exception as e:
        resp = {"error": str(e)}
    resp["time"] = (datetime.now()-start).seconds
    return jsonResponse(resp)


@staff_member_required
def cause_error(request):
    resp = {}
    logger.error("This is a simple error")
    try:
        erorr = excepting
    except Exception as e:
        logger.exception('An Exception has ocurred in the code')
    erorr = error
    return jsonResponse(resp)


@staff_member_required
def sheet_stats(request):
    from dateutil.relativedelta import relativedelta
    html  = ""

    html += "Total Sheets: %d\n" % db.sheets.find().count()
    html += "Public Sheets: %d\n" % db.sheets.find({"status": "public"}).count()


    html += "\nUnique Source Sheet creators per month:\n\n"
    start = datetime.today().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    months = 30
    for i in range(months):
        end   = start
        start = end - relativedelta(months=1)
        query = {"dateCreated": {"$gt": start.isoformat(), "$lt": end.isoformat()}}
        n = db.sheets.find(query).distinct("owner")
        html += "%s: %d\n" % (start.strftime("%b %y"), len(n))

    html += "\n\nAll time contributors:\n\n"
    all_sheet_makers = db.sheets.distinct("owner")
    public_sheet_makers = db.sheets.find({"status": "public"}).distinct("owner")
    public_contributors = set(db.history.distinct("user")+public_sheet_makers)
    all_contributors = set(db.history.distinct("user")+all_sheet_makers)

    html += "Public Sheet Makers: %d\n" % len(public_sheet_makers)
    html += "All Sheet Makers: %d\n" % len(all_sheet_makers)
    html += "Public Contributors: %d\n" % len(public_contributors)
    html += "Public Contributors and Source Sheet Makers: %d\n" % len(all_contributors)

    return HttpResponse("<pre>" + html + "<pre>")


@staff_member_required
def untagged_sheets(request):
    html = ""
    page = int(request.GET.get("page", 0))
    page_size = 100
    sheets = db.sheets.find({"status": "public", "tags": []}, {"id": 1, "title": 1}).limit(page_size).skip(page_size*page)

    for sheet in sheets:
        html += "<li><a href='/sheets/%d' target='_blank'>%s</a></li>" % (sheet["id"], strip_tags(sheet["title"]))
    html += "<br><a href='/admin/untagged-sheets?page=%d'>More ›</a>" % (page + 1)

    return HttpResponse("<html><h1>Untagged Public Sheets</h1><ul>" + html + "</ul></html>")



@staff_member_required
def spam_dashboard(request):

    from django.contrib.auth.models import User

    if request.method == 'POST':

        spam_sheet_ids = list(map(int, request.POST.getlist("spam_sheets[]", [])))
        reviewed_sheet_ids = list(map(int, request.POST.getlist("reviewed_sheets[]", [])))

        db.sheets.update_many({"id": {"$in": reviewed_sheet_ids}}, {"$set": {"reviewed": True}})

        spammers = db.sheets.find({"id": {"$in": spam_sheet_ids}}, {"owner": 1}).distinct("owner")

        for spammer in spammers:
            try:
                spammer_account = User.objects.get(id=spammer)
                spammer_account.is_active = False
                spammer_account.save()
            except:
                continue

        db.sheets.delete_many({"id": {"$in": spam_sheet_ids}})

        return render(request, 'spam_dashboard.html',
                      {"deleted_sheets": len(spam_sheet_ids),
                       "sheet_ids": spam_sheet_ids,
                       "reviewed_sheets": len(reviewed_sheet_ids),
                       "spammers_deactivated": len(spammers)
                       })

    else:
        date = request.GET.get("date", None)

        if date:
            date = datetime.strptime(date, '%Y-%m-%d')

        else:
            date = request.GET.get("date", datetime.now() - timedelta(days=30))

        earliest_new_user_id = User.objects.filter(date_joined__gte=date)[0].id

        regex = r'.*(?!href=[\'"](\/|http(s)?:\/\/(www\.)?sefaria).+[\'"])(href).*'
        sheets = db.sheets.find({"sources.ref": {"$exists": False}, "dateCreated": {"$gt": date.strftime("%Y-%m-%dT%H:%M:%S.%f")}, "owner": {"$gt": earliest_new_user_id}, "includedRefs": {"$size": 0}, "reviewed": {"$ne": True}, "$or": [{"sources.outsideText": {"$regex": regex}}, {"sources.comment": {"$regex": regex}}, {"sources.outsideBiText.en": {"$regex": regex}}, {"sources.outsideBiText.he": {"$regex": regex}}]})

        sheets_list = []

        for sheet in sheets:
            sheets_list.append({"id": sheet["id"], "title": strip_tags(sheet["title"]), "owner": user_link(sheet["owner"])})

        return render(request, 'spam_dashboard.html',
                      {"title": "Potential Spam Sheets since %s" % date.strftime("%Y-%m-%d"),
                       "sheets": sheets_list,
                       })

@staff_member_required
def versions_csv(request):
    return HttpResponse(make_versions_csv(), content_type="text/csv")

@csrf_exempt
def index_sheets_by_timestamp(request):
    import dateutil.parser
    from django.contrib.auth.models import User

    key = request.POST.get("apikey")
    if not key:
        return jsonResponse({"error": "You must be logged in or use an API key to index sheets by timestamp."})
    apikey = db.apikeys.find_one({"key": key})
    if not apikey:
        return jsonResponse({"error": "Unrecognized API key."})
    user = User.objects.get(id=apikey["uid"])
    if not user.is_staff:
        return jsonResponse({"error": "Only Sefaria Moderators can add or edit terms."})

    timestamp = request.POST.get('timestamp')
    try:
        dateutil.parser.parse(timestamp)
    except ValueError:
        return jsonResponse({"error": "Timestamp {} not valid".format(timestamp)})
    response_str = search_index_sheets_by_timestamp(timestamp)
    return jsonResponse({"success": response_str})

def library_stats(request):
    return HttpResponse(get_library_stats(), content_type="text/csv")


def core_link_stats(request):
    return HttpResponse(get_core_link_stats(), content_type="text/csv")


def run_tests(request):
    # This was never fully developed, methinks
    from subprocess import call
    from .local_settings import DEBUG
    if not DEBUG:
        return
    call(["/var/bin/run_tests.sh"])


@catch_error_as_http
def text_download_api(request, format, title, lang, versionTitle):

    content = _get_text_version_file(format, title, lang, versionTitle)

    content_types = {
        "json": "application/json; charset=utf-8",
        "csv": "text/csv; charset=utf-8",
        "txt": "text/plain; charset=utf-8",
        "plain.txt": "text/plain; charset=utf-8"
    }
    response = HttpResponse(content, content_type=content_types[format])
    response["Content-Disposition"] = "attachment"
    return response


@staff_member_required
@catch_error_as_http
def bulk_download_versions_api(request):

    format = request.GET.get("format")
    title_pattern = request.GET.get("title_pattern")
    version_title_pattern = request.GET.get("version_title_pattern")
    language = request.GET.get("language")

    error = None
    if not format:
        error = "A value is required for 'format'"
    if not title_pattern and not version_title_pattern:
        error = "A value is required for either 'title_pattern' or 'version_title_pattern'"
    if error:
        return jsonResponse({"error": error})

    query = {}
    if title_pattern:
        query["title"] = {"$regex": title_pattern}
    if version_title_pattern:
        query["versionTitle"] = {"$regex": version_title_pattern}
    if language:
        query["language"] = language

    vs = VersionSet(query)

    if len(vs) == 0:
        return jsonResponse({"error": "No versions found to match query"})

    file_like_object = io.BytesIO()
    with zipfile.ZipFile(file_like_object, "a", zipfile.ZIP_DEFLATED) as zfile:
        for version in vs:
            filebytes = _get_text_version_file(format, version.title, version.language, version.versionTitle)
            name = '{} - {} - {}.{}'.format(version.title, version.language, version.versionTitle, format).encode('utf-8')
            if isinstance(filebytes, str):
                filebytes = filebytes.encode('utf-8')
            zfile.writestr(name, filebytes)

    content = file_like_object.getvalue()
    response = HttpResponse(content, content_type="application/zip")
    filename = "{}-{}-{}-{}.zip".format(list(filter(str.isalnum, str(title_pattern))), list(filter(str.isalnum, str(version_title_pattern))), language, format).encode('utf-8')
    response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
    return response


def _get_text_version_file(format, title, lang, versionTitle):
    from sefaria.export import text_is_copyright, make_json, make_text, prepare_merged_text_for_export, prepare_text_for_export, export_merged_csv, export_version_csv

    assert lang in ["en", "he"]
    assert format in ["json", "csv", "txt", "plain.txt"]
    merged = versionTitle == "merged"
    index = library.get_index(title)

    if merged:
        if format == "csv" and merged:
            content = export_merged_csv(index, lang)

        elif format == "json" and merged:
            content = make_json(prepare_merged_text_for_export(title, lang=lang))

        elif format == "txt" and merged:
            content = make_text(prepare_merged_text_for_export(title, lang=lang))

        elif format == "plain.txt" and merged:
            content = make_text(prepare_merged_text_for_export(title, lang=lang), strip_html=True)

    else:
        version_query = {"title": title, "language": lang, "versionTitle": versionTitle}

        if format == "csv":
            version = Version().load(version_query)
            assert version, "Can not find version of {} in {}: {}".format(title, lang, versionTitle)
            assert not version.is_copyrighted(), "Cowardly refusing to export copyrighted text."
            content = export_version_csv(index, [version])
        else:
            version_object = db.texts.find_one(version_query)
            assert version_object, "Can not find version of {} in {}: {}".format(title, lang, versionTitle)
            assert not text_is_copyright(version_object), "Cowardly refusing to export copyrighted text."

            if format == "json":
                content = make_json(prepare_text_for_export(version_object))

            elif format == "txt":
                content = make_text(prepare_text_for_export(version_object))

            elif format == "plain.txt":
                content = make_text(prepare_text_for_export(version_object), strip_html=True)

    return content



@staff_member_required
def text_upload_api(request):
    if request.method != "POST":
        return jsonResponse({"error": "Unsupported Method: {}".format(request.method)})

    from sefaria.export import import_versions_from_stream
    message = ""
    files = request.FILES.getlist("texts[]")
    for f in files:
        try:
            import_versions_from_stream(f, [1], request.user.id)
            message += "Imported: {}.  ".format(f.name)
        except Exception as e:
            return jsonResponse({"error": str(e), "message": message})

    message = "Successfully imported {} versions".format(len(files))
    return jsonResponse({"status": "ok", "message": message})

@staff_member_required
def modtools_upload_workflowy(request):
    from sefaria.helper.text import WorkflowyParser
    if request.method != "POST":
        return jsonResponse({"error": "Unsupported Method: {}".format(request.method)})

    file = request.FILES['wf_file']
    c_index = request.POST.get("c_index", False)
    c_version = request.POST.get("c_version", False)
    delims = request.POST.get("delims", None) if len(request.POST.get("delims", None)) else None
    term_scheme = request.POST.get("term_scheme", None) if len(request.POST.get("term_scheme", None)) else None

    uid = request.user.id
    try:
        wfparser = WorkflowyParser(file, uid, term_scheme=term_scheme, c_index=c_index, c_version=c_version, delims=delims)
        res = wfparser.parse()
    except Exception as e:
        raise e #this will send the django error html down to the client... ¯\_(ツ)_/¯ which is apparently what we want

    return jsonResponse({"status": "ok", "data": res})

def compare(request, secRef=None, lang=None, v1=None, v2=None):
    if secRef and Ref.is_ref(secRef):
        secRef = Ref(secRef).first_available_section_ref()
        if not secRef.is_section_level():
            secRef = secRef.section_ref()
        secRef = secRef.normal()
    if v1:
        v1 = v1.replace("_", " ")
    if v2:
        v2 = v2.replace("_", " ")

    return render(request,'compare.html', {"JSON_PROPS": json.dumps({
        'secRef': secRef,
        'v1': v1, 'v2': v2,
        'lang': lang,})})
