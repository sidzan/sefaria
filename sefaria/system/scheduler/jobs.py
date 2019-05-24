
from sefaria.model.story import TextPassageStoryFactory, AuthorStoryFactory, TopicListStoryFactory, \
    TopicTextsStoryFactory, UserSheetsFactory, GroupSheetListFactory, SheetListFactory


def add_jobs(scheduler):
    _add_calendar_jobs(scheduler)
    _add_parasha_jobs(scheduler)

    scheduler.add_job(TopicListStoryFactory.create_trending_story,  "cron", id="TopicList", replace_existing=True,
                      day_of_week="mon,wed,fri", hour="2", minute="2")

    scheduler.add_job(TopicTextsStoryFactory.create_random_shared_story,  "cron", id="RandTopic", replace_existing=True,
                      day_of_week="tue,thu,sun", hour="2", minute="4")

    scheduler.add_job(AuthorStoryFactory.create_random_shared_story, "cron", id="RandAuthor", replace_existing=True,
                      day_of_week="tue,thu", hour="2", minute="6")

    scheduler.add_job(SheetListFactory.create_featured_story, "cron", id="FeaturedSheets", replace_existing=True,
                      day_of_week="wed", hour="2", minute="8")


def _add_parasha_jobs(scheduler):
    scheduler.add_job(TextPassageStoryFactory.create_aliyah, "cron", id="Aliyah", replace_existing=True,
                      day_of_week="sun, mon, tue, wed, thu, fri", hour="0", minute="5")

    scheduler.add_job(TextPassageStoryFactory.create_haftarah, "cron", id="Haftarah", replace_existing=True,
                      day_of_week="fri, sun", hour="0", minute="3")

    scheduler.add_job(SheetListFactory.create_parasha_sheets_stories, "cron", id="Parasha_Sheets1", replace_existing=True,
                      day_of_week="mon", hour="3", minute="5")

    scheduler.add_job(SheetListFactory.create_parasha_sheets_stories, "cron", id="Parasha_Sheets2", replace_existing=True,
                      kwargs={"page": 1}, day_of_week="wed", hour="3", minute="5")

    scheduler.add_job(SheetListFactory.create_parasha_sheets_stories, "cron", id="Parasha_Sheets3", replace_existing=True,
                      kwargs={"page": 2}, day_of_week="fri", hour="3", minute="5")

    scheduler.add_job(TopicListStoryFactory.create_parasha_topics_stories, "cron", id="Parasha_Topics1", replace_existing=True,
                      day_of_week="sun", hour="3", minute="5")

    scheduler.add_job(TopicListStoryFactory.create_parasha_topics_stories, "cron", id="Parasha_Topics2", replace_existing=True,
                      kwargs={"page": 1}, day_of_week="tue", hour="3", minute="5")


def _add_calendar_jobs(scheduler):
    scheduler.add_job(TextPassageStoryFactory.create_daf_yomi, "cron", id="DafYomi", replace_existing=True,
                      hour="0", minute="10")

    scheduler.add_job(TextPassageStoryFactory.create_929, "cron", id="929", replace_existing=True,
                      day_of_week="mon, tue, wed, thu, sun", hour="0", minute="12")

    scheduler.add_job(TextPassageStoryFactory.create_daily_mishnah, "cron", id="Mishnah", replace_existing=True,
                      hour="0", minute="15")
