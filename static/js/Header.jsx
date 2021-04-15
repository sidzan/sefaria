import React, { useState, useEffect, useRef} from 'react';
import PropTypes  from 'prop-types';
import ReactDOM  from 'react-dom';
import Component from 'react-class';
import classNames  from 'classnames';
import $  from './sefaria/sefariaJquery';
import Sefaria  from './sefaria/sefaria';
import {
  ReaderNavigationMenuSearchButton,
  GlobalWarningMessage,
  ProfilePic,
  InterfaceLanguageMenu,
  InterfaceText,
} from './Misc';


class Header extends Component {
  componentDidMount() {
    window.addEventListener('keydown', this.handleFirstTab);
  }
  handleFirstTab(e) {
    if (e.keyCode === 9) { // tab (i.e. I'm using a keyboard)
      document.body.classList.add('user-is-tabbing');
      window.removeEventListener('keydown', this.handleFirstTab);
    }
  }
  render() {
    const headerInnerClasses = classNames({
      headerInner: 1,
      boxShadow: this.props.hasBoxShadow,
      mobileHeader: !this.props.multiPanel
    });
        
    const headerContent = (
      <>
        <div className="headerNavSection">
            { Sefaria._siteSettings.TORAH_SPECIFIC ? <a className="home" href="/" ><img src="/static/img/logo.svg" alt="Sefaria Logo"/></a> : null }
            <a href="/texts" className="library"><InterfaceText>Texts</InterfaceText></a>
            <a href="/topics" className="library"><InterfaceText>Topics</InterfaceText></a>
            <a  href="https://sefaria.nationbuilder.com/supportsefaria" target="_blank" className="library"><InterfaceText>Donate</InterfaceText></a>
        </div>

        <div className="headerLinksSection">
          
          <SearchBar 
            onRefClick={this.props.onRefClick}
            showSearch={this.props.showSearch}
            openTopic={this.props.openTopic}
            openURL={this.props.openURL} />

          { Sefaria._uid ?
            <LoggedInButtons headerMode={this.props.headerMode}/>
            : <LoggedOutButtons headerMode={this.props.headerMode}/>
          }
          { !Sefaria._uid && Sefaria._siteSettings.TORAH_SPECIFIC ? 
              <InterfaceLanguageMenu currentLang={Sefaria.interfaceLang} /> : null}
        </div>
      </>
    );
    
    const mobileHeaderContent = (
      <>
        <div>
          <a href="/texts" aria-label={Sefaria._("Menu")} className="library">
            <i className="fa fa-bars"></i>
          </a>
        </div>
        
        <div className="mobileHeaderCenter">
          { Sefaria._siteSettings.TORAH_SPECIFIC ? 
          <a className="home" href="/" >
            <img src="/static/img/logo.svg" alt="Sefaria Logo"/>
          </a> : null }
        </div>
        
        <div></div>
      </>
    );

    return (
      <div className="header" role="banner">
        <div className={headerInnerClasses}>
          {this.props.multiPanel ? headerContent : mobileHeaderContent}
        </div>
        <GlobalWarningMessage />
      </div>
    );
  }
}
Header.propTypes = {
  multiPanel:   PropTypes.bool.isRequired,
  headerMode:   PropTypes.bool.isRequired,
  onRefClick:   PropTypes.func.isRequired,
  showSearch:   PropTypes.func.isRequired,
  openTopic:    PropTypes.func.isRequired,
  openURL:      PropTypes.func.isRequired,
  hasBoxShadow: PropTypes.bool.isRequired,
};


class SearchBar extends Component {
  constructor(props) {
    super(props);

    this.state = {
      searchFocused: false
    };
    this._searchOverridePre = Sefaria._('Search for') +': "';
    this._searchOverridePost = '"';
    this._type_icon_map = {
      "Collection": "collection.svg",
      "Person": "iconmonstr-pen-17.svg",
      "TocCategory": "iconmonstr-view-6.svg",
      "Topic": "iconmonstr-hashtag-1.svg",
      "ref": "iconmonstr-book-15.svg",
      "search": "iconmonstr-magnifier-2.svg",
      "Term": "iconmonstr-script-2.svg",
    }
  }
  componentDidMount() {
    this.initAutocomplete();
    window.addEventListener('keydown', this.handleFirstTab);
  }
  _type_icon(item) {
    if (item.type === "User") {
      return item.pic;
    } else {
      return `/static/icons/${this._type_icon_map[item.type]}`;
    }
  }
  _searchOverrideRegex() {
    return RegExp(`^${RegExp.escape(this._searchOverridePre)}(.*)${RegExp.escape(this._searchOverridePost)}`);
  }
  // Returns true if override is caught.
  catchSearchOverride(query) {
    const override = query.match(this._searchOverrideRegex());
    if (override) {
      if (Sefaria.site) {
        Sefaria.track.event("Search", "Search Box Navigation - Book Override", override[1]);
      }
      this.closeSearchAutocomplete();
      this.showSearch(override[1]);
      $(ReactDOM.findDOMNode(this)).find("input.search").val(override[1]);
      return true;
    }
    return false;
  }
  initAutocomplete() {
    $.widget( "custom.sefariaAutocomplete", $.ui.autocomplete, {
      _renderItem: function(ul, item) {
        const override = item.label.match(this._searchOverrideRegex());
        const is_hebrew = Sefaria.hebrew.isHebrew(item.label);
        return $( "<li></li>" )
          .addClass('ui-menu-item')
          .data( "item.autocomplete", item )
          .toggleClass("search-override", !!override)
          .toggleClass("hebrew-result", !!is_hebrew)
          .toggleClass("english-result", !is_hebrew)
          .append(`<img alt="${item.type}" class="ac-img-${item.type}" src="${this._type_icon(item)}">`)
          .append( $(`<a href="${this.getURLForObject(item.type, item.key)}" role='option' data-type-key="${item.type}-${item.key}"></a>` ).text( item.label ) )
          .appendTo( ul );
      }.bind(this)
    });
    const anchorSide = Sefaria.interfaceLang === "hebrew" ? "right+" : "left-";
    const sideGap = Sefaria.interfaceLang === "hebrew" ? 38 : 40;
    $(ReactDOM.findDOMNode(this)).find("input.search").sefariaAutocomplete({
      position: {my: anchorSide + sideGap + " top+18", at: anchorSide + "0 bottom"},
      minLength: 3,
      open: function($event, ui) {
          const $widget = $("ul.ui-autocomplete");
          $(".readerApp > .header").append($widget);
      },
      select: ( event, ui ) => {
        event.preventDefault();

        if (this.catchSearchOverride(ui.item.label)) {
          return false;
        }

        this.redirectToObject(ui.item.type, ui.item.key);
        return false;
      },
      focus: ( event, ui ) => {
        event.preventDefault();
        $(ReactDOM.findDOMNode(this)).find("input.search").val(ui.item.label);
        $(".ui-state-focus").removeClass("ui-state-focus");
        $(`.ui-menu-item a[data-type-key="${ui.item.type}-${ui.item.key}"]`).parent().addClass("ui-state-focus");
      },
      source: (request, response) => Sefaria.getName(request.term)
        .then(d => {
          const comps = d["completion_objects"].map(o => {
            const c = {...o};
            c["value"] = `${o['title']}${o["type"] === "ref" ? "" :` (${o["type"]})`}`;
            c["label"] = o["title"];
            return c;
          });
          if (comps.length > 0) {
            const q = `${this._searchOverridePre}${request.term}${this._searchOverridePost}`;
            response(comps.concat([{value: "SEARCH_OVERRIDE", label: q, type: "search"}]));
          } else {
            response([])
          }
        }, e => response([]))
    });
  }
  showVirtualKeyboardIcon(show){
      if(document.getElementById('keyboardInputMaster')){ //if keyboard is open, ignore.
        return; //this prevents the icon from flashing on every key stroke.
      }
      if(Sefaria.interfaceLang === 'english'){
          $(ReactDOM.findDOMNode(this)).find(".keyboardInputInitiator").css({"display": show ? "inline" : "none"});
      }
  }
  focusSearch(e) {
    const parent = document.getElementById('searchBox');
    this.setState({searchFocused: true});
    this.showVirtualKeyboardIcon(true);
  }
  blurSearch(e) {
    // check that you're actually focusing in on element outside of searchBox
    // see 2nd answer https://stackoverflow.com/questions/12092261/prevent-firing-the-blur-event-if-any-one-of-its-children-receives-focus/47563344
    const parent = document.getElementById('searchBox');
    if (!parent.contains(e.relatedTarget)) {
      if (!document.getElementById('keyboardInputMaster')) {
        // if keyboard is open, don't just close it and don't close search
        this.setState({searchFocused: false});
      }
      this.showVirtualKeyboardIcon(false);
    }
  }
  showSearch(query) {
    query = query.trim();
    if (typeof sjs !== "undefined") {
      query = encodeURIComponent(query);
      window.location = `/search?q=${query}`;
      return;
    }
    this.props.showSearch(query);
    $(ReactDOM.findDOMNode(this)).find("input.search").sefariaAutocomplete("close");
  }
  getURLForObject(type, key) {
    if (type === "Person") {
      return `/person/${key}`;
    } else if (type === "Collection") {
      return `/collections/${key}`;
    } else if (type === "TocCategory") {
      return `/texts/${key.join('/')}`;
    } else if (type === "Topic") {
      return `/topics/${key}`;
    } else if (type === "ref") {
      return `/${key.replace(/ /g, '_')}`;
    } else if (type === "User") {
      return `/profile/${key}`;
    }
  }
  redirectToObject(type, key) {
      Sefaria.track.event("Search", `Search Box Navigation - ${type}`, key);
      this.closeSearchAutocomplete();
      this.clearSearchBox();
      const url = this.getURLForObject(type, key);
      const handled = this.props.openURL(url);
      if (!handled) {
        window.location = url;
      }
  }
  submitSearch(query) {
    Sefaria.getName(query)
      .then(d => {
        // If the query isn't recognized as a ref, but only for reasons of capitalization. Resubmit with recognizable caps.
        if (Sefaria.isACaseVariant(query, d)) {
          this.submitSearch(Sefaria.repairCaseVariant(query, d));
          return;
        }

        if (d["is_ref"]) {
          var action = d["is_book"] ? "Search Box Navigation - Book" : "Search Box Navigation - Citation";
          Sefaria.track.event("Search", action, query);
          this.clearSearchBox();
          this.props.onRefClick(d["ref"]);  //todo: pass an onError function through here to the panel onError function which redirects to search
        } else if (!!d["topic_slug"]) {
          Sefaria.track.event("Search", "Search Box Navigation - Topic", query);
          this.clearSearchBox();
          this.props.openTopic(d["topic_slug"]);
        } else if (d["type"] === "Person" || d["type"] === "Collection" || d["type"] === "TocCategory") {
          this.redirectToObject(d["type"], d["key"]);
        } else {
          Sefaria.track.event("Search", "Search Box Search", query);
          this.closeSearchAutocomplete();
          this.showSearch(query);
        }
      });
  }
  closeSearchAutocomplete() {
    $(ReactDOM.findDOMNode(this)).find("input.search").sefariaAutocomplete("close");
  }
  clearSearchBox() {
    $(ReactDOM.findDOMNode(this)).find("input.search").val("").sefariaAutocomplete("close");
  }
  handleSearchKeyUp(event) {
    if (event.keyCode !== 13 || $(".ui-state-focus").length > 0) { return; }
    const query = $(event.target).val();
    if (!query) { return; }
    if (this.catchSearchOverride(query)) { return; }
    this.submitSearch(query);
  }
  handleSearchButtonClick(event) {
    const query = $(ReactDOM.findDOMNode(this)).find(".search").val();
    if (query) {
      this.submitSearch(query);
    } else {
      $(ReactDOM.findDOMNode(this)).find(".search").focus();
    }
  }
  render() {
    const inputClasses = classNames({
      search: 1,
      keyboardInput: Sefaria.interfaceLang === "english",
      hebrewSearch: Sefaria.interfaceLang === "hebrew"
    });
    const searchBoxClasses = classNames({searchBox: 1, searchFocused: this.state.searchFocused});

    return (
      <div id="searchBox" className={searchBoxClasses}>
        <ReaderNavigationMenuSearchButton onClick={this.handleSearchButtonClick} />
        <input className={inputClasses}
               id="searchInput"
               placeholder={Sefaria._("Search")}
               onKeyUp={this.handleSearchKeyUp}
               onFocus={this.focusSearch}
               onBlur={this.blurSearch}
               maxLength={75}
        title={Sefaria._("Search for Texts or Keywords Here")}/>
      </div>
    );
  }
}
SearchBar.propTypes = {
  onRefClick:   PropTypes.func.isRequired,
  showSearch:   PropTypes.func.isRequired,
  openTopic:    PropTypes.func.isRequired,
};


const LoggedOutButtons = ({headerMode}) => {
  const [isClient, setIsClient] = useState(false);
  const [next, setNext] = useState("/");
  const [loginLink, setLoginLink] = useState("/login?next=/");
  const [registerLink, setRegisterLink] = useState("/register?next=/");
  useEffect(()=>{
    setIsClient(true);
  }, []);
  useEffect(()=> {
    if(isClient){
      setNext(encodeURIComponent(Sefaria.util.currentPath()));
      setLoginLink("/login?next="+next);
      setRegisterLink("/register?next="+next);
    }
  })
  return(
    <div className="accountLinks anon">
      <a className="login loginLink" href={loginLink} key={`login${isClient}`}>
         <span className="int-en">Log in</span>
         <span className="int-he">התחבר</span>
       </a>
      <a className="login signupLink" href={registerLink} key={`register${isClient}`}>
         <span className="int-en">Sign up</span>
         <span className="int-he">הרשם</span>
      </a>
    </div>
  );
}


const LoggedInButtons = ({headerMode}) => {
  const [isClient, setIsClient] = useState(false);
  useEffect(()=>{
    if(headerMode){
      setIsClient(true);
    }
  }, []);
  const unread = headerMode ? ((isClient && Sefaria.notificationCount > 0) ? 1 : 0) : Sefaria.notificationCount > 0 ? 1 : 0
  const notificationsClasses = classNames({notifications: 1, unread: unread});
  return(
      <div className="accountLinks">
          <a href="/texts/saved" aria-label="See My Saved Texts">
            <img src="/static/icons/bookmarks.svg" />
          </a>      
          <a href="/notifications" aria-label="See New Notifications" key={`notificationCount-C-${unread}`} className={notificationsClasses}>
            <img src="/static/icons/notification.svg" />
          </a>
          <a href="/my/profile" className="my-profile">
            <ProfilePic len={24} url={Sefaria.profile_pic_url} name={Sefaria.full_name} key={`profile-${isClient}-${Sefaria.full_name}`}/>
          </a>
       </div>
  );
}


export default Header;