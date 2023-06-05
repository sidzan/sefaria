import React, {useRef, useState} from "react";
import Sefaria from "./sefaria/sefaria";
import {AdminToolHeader, InterfaceText} from "./Misc";
import sanitizeHtml  from 'sanitize-html';
import MDEditor, { commands } from '@uiw/react-md-editor';

const AdminEditorButton = ({toggleAddingTopics, text}) => {
    return <div onClick={toggleAddingTopics} id="editTopic" className="button extraSmall topic" role="button">
        <InterfaceText>{text}</InterfaceText>
    </div>;
}

function useEditToggle() {
  const [editingBool, toggleEditingBool] = useState(false);
  const toggleAddingTopics = function(e) {
      if (e.currentTarget.id === "editTopic") {
        toggleEditingBool(true);
      }
      else if(e.currentTarget.id === "cancel") {
        toggleEditingBool(false);
     }
  }
  return [editingBool, toggleAddingTopics];
}

const MarkdownWrapper = ({field, data, placeholder, updateData}) => {
    const [links, setLinks] = useState([]);
    const validate = async (element, i, parent) => {
        if (element.tagName === 'a') {
            if (links.indexOf(element.properties.href) >= 0) {
                return true;
            } else {
                const name = element.properties.href.split("/").slice(-1)[0];
                let d;
                d = element.properties.href.startsWith("/topics") ?
                    await Sefaria.getTopicCompletions(name, (x) => x[1])
                    : await Sefaria.getName(name, false).completion_objects;
                const namesFound = d.map((x) => x.key);
                const validLink = namesFound.indexOf(name) > 0 ? true :
                    confirm(`${name} not found in Sefaria database.  Did you mean to write ${element.properties.href} be in the description?`);
                if (validLink) {
                    const newLinks =  [...links];
                    newLinks.push(element.properties.href);
                    setLinks(newLinks);
                }
            }

        }
    }
    const setTextareaValue = (newVal, e) => {
        data[e.target.id] = newVal;
        updateData({...data});
    }
    return <MDEditor textareaProps={{id: field, placeholder: Sefaria._(placeholder)}}
                                      commands={[commands.bold, commands.italic, commands.link]}
                                      previewOptions={{allowElement: validate}}
                                      value={data[field]} onChange={setTextareaValue} />
}

const AdminEditor = ({title, data, close, catMenu, updateData, savingStatus,
                         validate, deleteObj, items=[], isNew=true, extras=[], path=[]}) => {

    const setInputValue = (e) => {
        if (data.hasOwnProperty(e.target.id)) {
            data[e.target.id] = e.target.value;
        }
        updateData({...data});
    }
    const item = ({label, field, placeholder, textarea}) => {
        return  <div className="section">
                        <label><InterfaceText>{label}</InterfaceText></label>
                        {textarea ?
                            <MarkdownWrapper field={field} placeholder={placeholder} data={data} updateData={updateData}/>
                           : <input type='text' id={field} onBlur={setInputValue} defaultValue={data[field]} placeholder={Sefaria._(placeholder)}/>}
                    </div>;
    }
    const options_for_form = {
        "Title": {label: "Title", field: "enTitle", placeholder: "Add a title."},
        "Hebrew Title": {label: "Hebrew Title", field: "heTitle", placeholder: "Add a title."},
        "English Description": {label: "English Description", field: "enDescription", placeholder: "Add a description.", textarea: true},
        "Hebrew Description": {label: "Hebrew Description", field: "heDescription", placeholder: "Add a description.", textarea: true},
        "Prompt": {label: "Prompt", field: "prompt", placeholder:"Add a prompt.", textarea: true},
        "English Short Description": {label: "English Short Description for Table of Contents", field: "enCategoryDescription",
            placeholder: "Add a short description.", textarea: true},
        "Hebrew Short Description": {label: "Hebrew Short Description for Table of Contents", field: "heCategoryDescription",
            placeholder: "Add a short description.", textarea: true},
    }
    const preprocess = () => {
        // first look for markdown boxes and update data


        // sanitize markdown boxes
        items.map((x) => {
            if (options_for_form[x]?.textarea) {
                const field = options_for_form[x].field;
                data[field] = sanitizeHtml(data[field], {
                    allowedTags: [],
                    disallowedTagsMode: 'discard',
                });
            }
        });
        validate();
    }
    return <div className="editTextInfo">
            <div className="static">
                <div className="inner">
                    {savingStatus ?  <div className="collectionsWidget">{Sefaria._("Saving...")}</div> : null}
                    <div id="newIndex">
                        <AdminToolHeader title={title} close={close} validate={() => preprocess()}/>
                        {items.map((x) => {
                            if (x.includes("Hebrew") && (!Sefaria._siteSettings.TORAH_SPECIFIC)) {
                                return null;
                            }
                            else if (x === "Category Menu") {
                                return catMenu;
                            }
                            else {
                                return item({...options_for_form[x]});
                            }
                        })}
                        {extras}
                        {!isNew && <div onClick={deleteObj} id="deleteTopic" className="button small deleteTopic" tabIndex="0" role="button">
                                      <InterfaceText>Delete</InterfaceText>
                                    </div>}

                    </div>
                </div>
            </div>
     </div>
}

export {AdminEditor, AdminEditorButton, useEditToggle};