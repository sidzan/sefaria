import React  from 'react';
import PropTypes  from 'prop-types';
import Component from 'react-class';
import $  from './sefaria/sefariaJquery';
import Sefaria  from './sefaria/sefaria';
import { IntText } from './Misc';


class EditGroupPage extends Component {
  constructor(props) {
    super(props);

    this.state = props.initialData || {
        name: null,
        description: null,
        websiteUrl: null,
        imageUrl: null,
        headerUrl: null,
        listed: false
    };
  }
  componentDidMount() {
    $(window).on("beforeunload", function() {
      if (this.changed) {
        return Sefaria._("You have unsaved changes to your collection.");
      }
    }.bind(this));
  }
  handleImageChange(e) {
    var MAX_IMAGE_MB = 2;
    var MAX_IMAGE_SIZE = MAX_IMAGE_MB * 1024 * 1024;
    var idToField = {
      groupHeader: "headerUrl",
      groupImage: "imageUrl",
    };
    var field = idToField[e.target.id];
    var file = e.currentTarget.files[0];
    if (file.size > MAX_IMAGE_SIZE) {
      alert(Sefaria._("Images must be smaller than ") + MAX_IMAGE_MB + "MB.");
      return;
    }
    var formData = new FormData();
    formData.append("file", e.currentTarget.files[0])
    $.ajax({
        url: '/api/file/upload',
        data: formData,
        type: 'POST',
        contentType: false,
        processData: false,
        success: function(data) {
          if ("error" in data) {
            alert(data.error);
            this.clearUploading(field);
          } else {
            var state = {};
            state[field] = data.url;
            this.setState(state);
            this.changed = true;
          }
        }.bind(this),
        fail: function() {
          alert(Sefaria._("Unfortunately an error occurred uploading your file."))
          this.clearUploading(field);
        }
    });
    this.setUploading(field);
  }
  setUploading(field) {
    var state = {};
    state[field] = "/static/img/loading.gif";
    this.setState(state);
  }
  clearUploading(field) {
    var state = {};
    state[field] = null;
    this.setState(state);
  }
  handleInputChange(e) {
    var idToField = {
      groupName: "name",
      groupWebsite: "websiteUrl",
      groupDescription: "description"
    }
    var field = idToField[e.target.id];
    var state = {};
    state[field] = e.target.value;
    this.setState(state);
    this.changed = true;
  }
  handleListingChange(e) {
    this.setState({listed: !!e.target.checked});
  }
  delete() {
    if (confirm(Sefaria._("Are you sure you want to delete this collection? This cannot be undone."))) {
     $.ajax({
        url: "/api/groups/" + this.props.initialData.slug,
        type: "DELETE",
        success: function(data) {
          if ("error" in data) {
            alert(data.error);
          } else {
            window.location = "/my/profile";
          }
        },
        fail: function() {
          alert(Sefaria._("Unfortunately an error occurred deleting your collection."));
        }
      });
    }
  }
  save() {
    var groupData = Sefaria.util.clone(this.state);

    if (groupData["headerUrl"] == "/static/img/loading.gif") { groupData["headerUrl"] = null; }
    if (groupData["imageUrl"] == "/static/img/loading.gif") { groupData["imageUrl"] = null; }

    $.post("/api/groups", {json: JSON.stringify(groupData)}, function(data) {
        if ("error" in data) {
          alert(data.error);
        } else {
          this.changed = false;
          window.location = "/collections/" + data.collection.slug;
        }
    }.bind(this)).fail(function() {
        alert(Sefaria._("Unfortunately an error occurred saving your collection."));
    });
  }
  render() {
    const title = this.props.initialData ? "Edit Collection" : "Create a Collection";
    return (
      <div id="editGroupPage">
        <div className="headerWithButtons">
          <div className="start"></div>
          <h1>
            <IntText>{title}</IntText>
          </h1>
          <div className="end">
              <a className="button transparent control-elem" href={this.props.initialData ? "/collections/" + this.state.slug : "/my/profile"}>
                  <IntText>Cancel</IntText>
              </a>
              <div id="saveGroup" className="button blue control-elem" onClick={this.save}>
                  <IntText>Save</IntText>
              </div>
          </div>
        </div>

        <div className="field halfWidth">
          <label>
            <IntText>Collection Name</IntText>
          </label>
          <input id="groupName" value={this.state.name||""} onChange={this.handleInputChange}/>
        </div>

        <div className="field halfWidth">
          <label>
            <IntText>Website</IntText>
          </label>
          <input id="groupWebsite" value={this.state.websiteUrl||""} onChange={this.handleInputChange}/>
        </div>

        <div className="field">
          <label>
            <IntText>Description</IntText>
          </label>
          <textarea id="groupDescription" onChange={this.handleInputChange} value={this.state.description||""}></textarea>
        </div>

        <div className="field">
          <label>
            <IntText>Collection Image</IntText>
          </label>
          {this.state.imageUrl
            ? <img className="groupImage" src={this.state.imageUrl} alt="Collection Image" />
            : <div className="groupImage placeholder"></div>}
          <FileInput
             name="groupImage"
             accept="image/*"
             text={Sefaria._("Upload Image")}
             className="button white"
             onChange={this.handleImageChange} />
          <div className="helperText">
            <IntText>Recommended size: 350px x 350px or larger</IntText>
          </div>
        </div>

        {/* Header images are only supported for legacy collections which already had them */}
        {this.state.headerUrl ? 
        <div className="field">
          <label>
            <IntText>Default Sheet Header</IntText>
          </label>
          {this.state.headerUrl
            ? <div className="groupHeaderBox">
                <img className="groupHeader" src={this.state.headerUrl} alt="Collection Header Image" />
                <div className="clearFix"></div>
              </div>
            : <div className="groupHeader placeholder"></div>}
          <FileInput
             name="groupHeader"
             accept="image/*"
             text="Upload Image"
             className="button white"
             onChange={this.handleImageChange} />
          <div className="helperText">
            <IntText>Recommended size: 1000px width to fill sheet, smaller images align right</IntText>
          </div>
        </div>
        : null }

        <div className="field">
          <label>
              <IntText>List on Sefaria</IntText>
          </label>
          {this.state.moderationStatus !== "nolist" ?
          <div className="onoffswitch">
            <input type="checkbox"
              name="onoffswitch"
              className="onoffswitch-checkbox"
              id="groupPublicToggle"
              checked={!!this.state.listed}
              onChange={this.handleListingChange} />
            <label className="onoffswitch-label" htmlFor="groupPublicToggle">
                <span className="onoffswitch-inner"></span>
                <span className="onoffswitch-switch"></span>
            </label>
            <div className="helperText">
              <IntText>Your collection will appear on the public collections page where others can find it.</IntText>
            </div>
          </div>
          : <div>
              <span className="int-en">Your collection was previously made public, but our moderators determined it was not generally useful for all Sefaria users. Please contact <a href="mailto:hello@sefari.org">hello@sefaria.org</a> with any questions.</span>
              <span className="int-he">האסופה שלך הוגדרה כציבורית, אך המנהלים שלנו הגיעו למסקנה שהיא אינה רלוונטית לכלל משתמשי ספריא. לשאלות יש ליצור עימנו קשר בכתובת <a href="mailto:hello@sefari.org">hello@sefaria.org</a>.</span>
          </div> }
        </div>

        {this.props.initialData ?
          <div className="deleteGroup" onClick={this.delete}>
            <IntText>Delete Collection</IntText>
          </div>
          : null}

      </div>);
  }
}
EditGroupPage.propTypes = {
  initialData:  PropTypes.object // If present this view is for editing a group, otherwise for creating a new group
};


class FileInput extends Component {
  handleChange(e) {
    if (this.props.onChange) { this.props.onChange(e); }
  }
  render() {
    return (<div>
              <label htmlFor={this.props.name} className={this.props.className}>{this.props.text}</label>
              <input
                type="file"
                id={this.props.name}
                name={this.props.name}
                className="hiddenFileInput"
                accept={this.props.accept}
                onChange={this.handleChange} />
            </div>);
  }
}


export default EditGroupPage;
