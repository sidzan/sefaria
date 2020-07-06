import {
  LoadingMessage,
  LoginPrompt,
} from './Misc';
import React from 'react';
import ReactDOM from 'react-dom';
import $ from './sefaria/sefariaJquery';
import Sefaria from './sefaria/sefaria';
import classNames from 'classnames';
import PropTypes from 'prop-types';
import Component from 'react-class';


class AddToSourceSheetBox extends Component {
  // In the main app, the function `addToSourceSheet` is executed in the ReaderApp,
  // and collects the needed data from highlights and app state.
  // It is used in external apps, liked gardens.  In those cases, it's wrapped in AddToSourceSheetWindow,
  // refs and text are passed directly, and the add to source sheets API is invoked from within this object.
  constructor(props) {
    super(props);

    this.state = {
      sheetsLoaded: false,
      selectedSheet: null,
      sheetListOpen: false,
      showConfirm: false,
      showLogin: false,
    };
  }
  componentDidMount() {
    this.loadSheets();
  }
  componentDidUpdate(prevProps, prevState) {
    if (!prevProps.srefs.compare(this.props.srefs) || prevProps.nodeRef !=this.props.nodeRef) {
      this.setState({showConfirm: false});
    }
  }
  loadSheets() {
    if (!Sefaria._uid) {
      this.onSheetsLoad();
    } else {
      Sefaria.sheets.userSheets(Sefaria._uid, this.onSheetsLoad);
    }
  }
  onSheetsLoad() {
    this.setDefaultSheet();
    this.setState({sheetsLoaded: true});
  }
  setDefaultSheet() {
    if (this.state.selectedSheet) { return; }
    if (!Sefaria._uid) {
        this.setState({selectedSheet: {title: "Your Sheet"}});
    } else {
      var sheets = Sefaria.sheets.userSheets(Sefaria._uid);
      if (!sheets.length) {
        this.setState({selectedSheet: {title: "Create a New Sheet"}});
      } else {
        this.setState({selectedSheet: sheets[0]});
      }
    }
  }
  toggleSheetList() {
    if (!Sefaria._uid) {
      this.props.toggleSignUpModal()
    } else {
      this.setState({sheetListOpen: !this.state.sheetListOpen});
    }
  }
  selectSheet(sheet) {
    this.setState({selectedSheet: sheet, sheetListOpen: false});
  }
  copyNodeToSourceSheet() {
    if (!Sefaria._uid) { this.props.toggleSignUpModal() }
    if (!this.state.selectedSheet || !this.state.selectedSheet.id) { return; }
    if (!this.props.nodeRef) {
      this.props.addToSourceSheet(this.state.selectedSheet.id, this.confirmAdd);
    } else {
      const url     = "/api/sheets/" + this.state.selectedSheet.id + "/copy_source";
      $.post(url, {
          sheetID: this.props.nodeRef.split(".")[0],
          nodeID:this.props.nodeRef.split(".")[1]
      }, this.confirmAdd);
    }
  }
  addToSourceSheet() {
    if (!Sefaria._uid) { this.props.toggleSignUpModal() }
    if (!this.state.selectedSheet || !this.state.selectedSheet.id) { return; }
      const url     = "/api/sheets/" + this.state.selectedSheet.id + "/add";
      const language = this.props.contentLanguage;
      let source = {};
      if(this.props.en || this.props.he){ // legacy code to support a call to this component in Gardens.
        if(this.props.srefs){ //we are saving a ref + ref's text, generally all fields should be present.
          source.refs = this.props.srefs;
          source.en = this.props.en;
          source.he = this.props.he;
        }else{ // an outside free text is being passed in. theoretically supports any interface that passes this in. In practice only legacy Gardens code.
          if (this.props.en && this.props.he) {
            source.outsideBiText = {he: this.props.he, en: this.props.en};
          } else {
            source.outsideText = this.props.en || this.props.he;
          }
        }
      } else if (this.props.srefs) { //regular use - this is currently the case when the component is loaded in the sidepanel or in the modal component via profiles and notes pages
        source.refs = this.props.srefs;
        const { en, he } = this.props.currVersions; //the text we are adding may be non-default version
        if (he) { source["version-he"] = he; }
        if (en) { source["version-en"] = en; }

        // If something is highlighted and main panel language is not bilingual:
        // Use passed in language to determine which version this highlight covers.
        var selectedWords = this.props.selectedWords; //if there was highlighted single panel
        if (selectedWords && language != "bilingual") {
          source[language.slice(0,2)] = selectedWords;
        }
      }
      let postData = {source: JSON.stringify(source)};
      if (this.props.note) {
        postData.note = this.props.note;
      }
      $.post(url, postData, this.confirmAdd);
  }
  createSheet(refs) {
    const title = $(ReactDOM.findDOMNode(this)).find("input").val();
    if (!title) { return; }
    const sheet = {
      title: title,
      options: {numbered: 0},
      sources: []
    };
    let postJSON = JSON.stringify(sheet);
    $.post("/api/sheets/", {"json": postJSON}, function(data) {
      Sefaria.sheets.clearUserSheets(Sefaria._uid);
      this.selectSheet(data);
    }.bind(this));
  }
  confirmAdd() {
    if (this.props.srefs) {
      Sefaria.track.event("Tools", "Add to Source Sheet Save", this.props.srefs.join("/"));
    } else {
      Sefaria.track.event("Tools", "Add to Source Sheet Save", "Outside Source");
    }
    this.setState({showConfirm: true});
  }
  makeTitleRef(){
    if(this.props.srefs.length > 1){
      return {
        "en": Sefaria.joinRefsToDisplayStr(Sefaria.getRefFromCache(this.props.srefs[0]), Sefaria.getRefFromCache(this.props.srefs[this.props.srefs.length - 1]), "english"),
        "he": Sefaria.joinRefsToDisplayStr(Sefaria.getRefFromCache(this.props.srefs[0]), Sefaria.getRefFromCache(this.props.srefs[this.props.srefs.length - 1]), "hebrew")
      };
    }else{
      return {
        "en": Sefaria.getRefFromCache(this.props.srefs[0]).ref,
        "he": Sefaria.getRefFromCache(this.props.srefs[0]).heRef
      };
    }
  }
  render() {
    if (this.state.showConfirm) {
      return (<ConfirmAddToSheet sheet={this.state.selectedSheet} srefs={this.props.srefs} />);
    } else if (this.state.showLogin) {
      return (<div className="addToSourceSheetBox sans">
                <LoginPrompt />
              </div>);
    }
    const titleRef = this.makeTitleRef();
    const sheets     = Sefaria._uid ? Sefaria.sheets.userSheets(Sefaria._uid) : null;
    let sheetsList = Sefaria._uid && sheets ? sheets.map((sheet) => {
      let classes     = classNames({dropdownOption: 1, noselect: 1, selected: this.state.selectedSheet && this.state.selectedSheet.id == sheet.id});
      let title = sheet.title ? sheet.title.stripHtml() : Sefaria._("Untitled Source Sheet");
      let selectSheet = this.selectSheet.bind(this, sheet);
      return (<div className={classes} onClick={selectSheet} key={sheet.id}>{title}</div>);
    }) : (Sefaria._uid ? <LoadingMessage /> : null);

    // Uses
    return (
      <div className="addToSourceSheetBox noselect">
        <div className="addToSourceSheetBoxTitle">
          <span className="int-en">Selected Citation</span>
          <span className="int-he">מקור להוספה</span>
        </div>
        <div className="selectedRef">
          <span className="en">{titleRef["en"]}</span>
          <span className="he">{titleRef["he"]}</span>
        </div>
        <div className="addToSourceSheetBoxTitle">
          <span className="int-en">Add to</span>
          <span className="int-he">יעד להוספה</span>
        </div>
        <div className="dropdown">
          <div className={`dropdownMain noselect ${this.state.sheetListOpen ? "open" : ""}`} onClick={this.toggleSheetList}>
            {this.state.sheetsLoaded ? (this.state.selectedSheet.title === null ? Sefaria._("Untitled Source Sheet") : this.state.selectedSheet.title.stripHtml()) : <LoadingMessage messsage="Loading your sheets..." heMessage="טוען את דפי המקורות שלך"/>}          </div>
          {this.state.sheetListOpen ?
          <div className="dropdownListBox noselect">
            <div className="dropdownList noselect">
              {sheetsList}
            </div>
            <div className="newSheet noselect">
              <input className="newSheetInput noselect" placeholder={Sefaria._("Name New Sheet")}/>
              <div className="button small noselect" onClick={this.createSheet} >
                <span className="int-en">Create</span>
                <span className="int-he">דף מקורות חדש</span>
              </div>
             </div>
          </div>
          : null}
        </div>
        <div className="button noselect fillWidth" onClick={this.props.nodeRef ? this.copyNodeToSourceSheet : this.addToSourceSheet}>
          <span className="int-en noselect">Add to Sheet</span>
          <span className="int-he noselect">הוסף לדף המקורות</span>
        </div>
      </div>);
  }
}
AddToSourceSheetBox.propTypes = {
  srefs:              PropTypes.array,
  fullPanel:          PropTypes.bool,
  en:                 PropTypes.string,
  he:                 PropTypes.string,
  note:               PropTypes.string
};


class ConfirmAddToSheet extends Component {
  render() {
    //const titleRef = Sefaria.getRefFromCache(Sefaria.normRefList(this.props.srefs));
    const titleRef = Sefaria.getRefFromCache(this.props.srefs[0]);
    return (<div className="confirmAddToSheet addToSourceSheetBox">
              <div className="message">
                <span className="int-en">
                  <a href={`/${titleRef.ref}`}>{titleRef.ref}</a>
                  &nbsp;has been added to&nbsp;
                   <a href={"/sheets/" + this.props.sheet.id} target="_blank">{this.props.sheet.title}</a>.
                </span>
                <span className="int-he">
                  <a href={`/${titleRef.ref}`}>{titleRef.heRef}</a>
                   &nbsp;נוסף בהצלחה לדף המקורות&nbsp;
                  <a href={"/sheets/" + this.props.sheet.id} target="_blank">{this.props.sheet.title}</a>.
                </span>
              </div>
            </div>);
  }
}
ConfirmAddToSheet.propTypes = {
  srefs: PropTypes.array,
  sheet: PropTypes.object.isRequired
};


class AddToSourceSheetWindow extends Component {
  close () {
    if (this.props.close) {
      this.props.close();
    }
  }
  render () {
    var nextParam = "?next=" + encodeURIComponent(Sefaria.util.currentPath());

    return (<div className="addToSourceSheetModal">
      <div className="sourceSheetBoxTitle">
        <img src="/static/img/circled-x.svg" className="closeButton" aria-hidden="true" alt="Close" onClick={this.close}/>
        {Sefaria.loggedIn ? null : <span>
            In order to add this source to a sheet, please <a href={"/login" + nextParam}>log in.</a>
        </span>}
        <div className="clearFix"></div>
      </div>
      {Sefaria.loggedIn ?
        <AddToSourceSheetBox
          srefs = {this.props.srefs}
          en = {this.props.en}
          he = {this.props.he}
          note = {this.props.note}
        /> : null }
      </div>);
  }
}
AddToSourceSheetWindow.propTypes = {
  srefs:        PropTypes.array,
  close:        PropTypes.func,
  en:           PropTypes.string,
  he:           PropTypes.string,
  note:         PropTypes.string,
};

export {
  AddToSourceSheetBox,
  AddToSourceSheetWindow,
};
