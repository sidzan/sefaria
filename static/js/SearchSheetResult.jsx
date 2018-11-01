const React      = require('react');
const $          = require('./sefaria/sefariaJquery');
const Sefaria    = require('./sefaria/sefaria');
const PropTypes  = require('prop-types');
import Component      from 'react-class';


class SearchSheetResult extends Component {
    handleSheetClick(e) {
      var href = e.target.closest('a').getAttribute("href");
      e.preventDefault();
      var s = this.props.data._source;
      Sefaria.track.event("Search", "Search Result Sheet Click", `${this.props.query} - ${s.sheetId}`,
          {hitCallback: () => window.location = href}
      );
    }
    handleProfileClick(e) {
      var href = e.target.closest('a').getAttribute("href");
      e.preventDefault();
      var s = this.props.data._source;
      Sefaria.track.event("Search", "Search Result Sheet Owner Click", `${this.props.query} - ${s.sheetId} - ${s.owner_name}`,
          {hitCallback: () => window.location = href}
      );
    }
    get_snippet_markup(data) {
      let snippet = data.highlight.content.join("..."); // data.highlight ? data.highlight.content.join("...") : s.content;
      snippet = snippet.replace(/^[ .,;:!-)\]]+/, "");
      return { __html: snippet };
    }
    render() {
        const data = this.props.data;
        const s = data._source;
        var clean_title = $("<span>" + s.title + "</span>").text();
        var href = "/sheets/" + s.sheetId;
        return (
            <div className='result sheet_result'>
                <a href={href} onClick={this.handleSheetClick}>
                    <div className='result-title'>{clean_title}</div>
                    <div className="snippet" dangerouslySetInnerHTML={this.get_snippet_markup(data)}></div>
                </a>
              <a href={s.profile_url} onClick={this.handleProfileClick}>
                <div className="version">
                  <img className='img-circle owner_image' src={s.owner_image} alt={s.owner_name} />
                  <span className="owner-metadata">
                    <div className='owner_name'>{s.owner_name}</div>
                    <div className='tags-views'>{`${s.views} Views${(!!s.tags && s.tags.length) ? ' • ' : ''}${!!s.tags ? s.tags.join(', ') : ''}`}</div>
                  </span>
                </div>
              </a>
            </div>
        );
    }
}
SearchSheetResult.propTypes = {
  query: PropTypes.string,
  data: PropTypes.object
};


module.exports = SearchSheetResult;
