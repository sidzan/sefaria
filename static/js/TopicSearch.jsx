import React  from 'react';
import ReactDOM  from 'react-dom';
import PropTypes  from 'prop-types';
import classNames  from 'classnames';
import $  from './sefaria/sefariaJquery';
import Sefaria  from './sefaria/sefaria';
import Component from 'react-class'
import {Autocompleter, InterfaceText} from "./Misc";
import {TopicEditor} from "./TopicEditor";


class TopicSearch extends Component {
  constructor(props) {
    super(props);
    this.state = {
      showTopicEditor: false,
      value: "",
    };
  }

  getSuggestions = async (input) => {
    let results = {"inputValue": input, "previewText": null, "helperPromptText": null, "currentSuggestions": null,
                        "showAddButton": false};
    if (input === "") {
      return results;
    }
    const word = input.trim();
    const callback = (d) => {
        let topics = [];
        if (d[1].length > 0) {
          topics = d[1].slice(0, 4).map(function (e) {
                return {title: e.title, key: e.key}
              });
            }
        topics.push({title: this.props.createNewTopicStr+word, key: ""})
        return topics;
     };
    const completion_objects = await Sefaria._cachedApiPromise({url: Sefaria.apiHost + "/api/topic/completion/" + word, key: word,
                              store: Sefaria._topicCompletions, processor: callback});
    results.currentSuggestions = completion_objects
        .map(suggestion => ({
          name: suggestion.title,
          key: suggestion.key,
          type: suggestion.type,
          border_color: "#ffffff"
        }))

    results.showAddButton = true;
    return results;
  }

  validate(input, suggestions) {
    let match = false;
    suggestions.map(topic => {
      if (topic.name.toLowerCase() === input.toLowerCase()) {
        this.post(topic.key);
        match = true;
      }
    })
    if (!match) {
      alert("Please select an option through the dropdown menu.");
    }
  }

  post(slug) {
      const postJSON = JSON.stringify({"topic": slug});
      const srefs = this.props.srefs;
      const update = this.props.update;
      const reset = this.reset;
      $.post("/api/ref-topic-links/" + Sefaria.normRef(this.props.srefs), {"json": postJSON}, async function (data) {
        if (data.error) {
          alert(data.error);
        } else {
          const sectionRef = await Sefaria.getRef(Sefaria.normRef(srefs)).sectionRef;
          srefs.map(sref => {
            if (!Sefaria._refTopicLinks[sref]) {
              Sefaria._refTopicLinks[sref] = [];
            }
            Sefaria._refTopicLinks[sref].push(data);
          });
          if (!Sefaria._refTopicLinks[sectionRef]) {
            Sefaria._refTopicLinks[sectionRef] = [];
          }
          Sefaria._refTopicLinks[sectionRef].push(data);
          update();
          reset();
          alert("Topic added.");
        }
      }).fail(function (xhr, status, errorThrown) {
        alert("Unfortunately, there may have been an error saving this topic information: " + errorThrown);
      });
  }

  onClickSuggestionFunc = (title) => {
    if (title.startsWith(this.props.createNewTopicStr)) {
      this.setState({showTopicEditor: true, value: title.replace(this.props.createNewTopicStr, "")});
    }
  }
  reset = () => {
      this.setState({showTopicEditor: false, value: ""});
  }

  render() {
    return (
        <div>{this.state.showTopicEditor ? <TopicEditor origEn={this.state.value} close={this.reset} redirect={this.post}/> : null}
        <Autocompleter selectedRefCallback={this.validate}
                 getSuggestions={this.getSuggestions}
                 onClickSuggestionFunc={this.onClickSuggestionFunc}
                 initInputValue={this.state.value}
                 inputPlaceholder="Search for a Topic."
                 buttonTitle="Add Topic"
                 showSuggestionsOnSelect={false}
                 getColor={(selectedBool) => !selectedBool ? "#000000" : "#4B71B7"}
                 autocompleteClassNames="topicSearch addInterfaceInput"
        />
        </div>
    );
  }
}
TopicSearch.propTypes = {
  contextSelector:  PropTypes.string.isRequired, // CSS Selector for uniquely identifiable context that this is in.
  srefs: PropTypes.array.isRequired, //srefs of TopicList
  update: PropTypes.func.isRequired, //used to add topic to TopicList
  createNewTopicStr: PropTypes.string.isRequired // whatever should be displayed when there's an option to create new topic
};


export default TopicSearch;