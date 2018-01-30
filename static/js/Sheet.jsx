const {
  LoadingMessage,
} = require('./Misc');

const React = require('react');
const ReactDOM = require('react-dom');
const PropTypes = require('prop-types');
const classNames = require('classnames');
const $ = require('./sefaria/sefariaJquery');
const Sefaria = require('./sefaria/sefaria');
const sanitizeHtml = require('sanitize-html');
import Component from 'react-class'


class Sheet extends Component {
  componentDidMount() {
    this.ensureData();

  }

  getSheetFromCache() {
    return Sefaria.sheets.loadSheetByID(this.props.id);
  }

  getSheetFromAPI() {
    Sefaria.sheets.loadSheetByID(this.props.id, this.onDataLoad);
  }

  onDataLoad(data) {
    this.forceUpdate();

  }

  componentDidUpdate(prevProps, prevState) {
  }


  ensureData() {
    if (!this.getSheetFromCache()) {
      this.getSheetFromAPI();
    }
  }


  render() {
    var sheet = this.getSheetFromCache();
    var classes = classNames({sheetsInPanel: 1});

    if (!sheet) {
      return (<LoadingMessage />);
    }
    else {
      return (
        <div className={classes}>

          <SheetContent
            sources={sheet.sources}
            onRefClick={this.props.onRefClick}
            onSegmentClick={this.props.onSegmentClick}
          />
        </div>
      )
    }
  }
}


class SheetContent extends Component {

  cleanHTML(html) {
    var clean = sanitizeHtml(html, {
            allowedTags: [ 'blockquote', 'p', 'a', 'ul', 'ol',
              'nl', 'li', 'b', 'i', 'strong', 'em', 'small', 'big', 'span', 'strike', 'hr', 'br', 'div',
              'table', 'thead', 'caption', 'tbody', 'tr', 'th', 'td', 'pre' ],
            allowedAttributes: {
              a: [ 'href', 'name', 'target' ],
              img: [ 'src' ],
              p: ['style'],
              span: ['style'],
              div: ['style'],
            },
            allowedStyles: {
              '*': {
                'color': [/^\#(0x)?[0-9a-f]+$/i, /^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/],
                'background-color': [/^\#(0x)?[0-9a-f]+$/i, /^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/],
                'text-align': [/^left$/, /^right$/, /^center$/],
              }
            },
            exclusiveFilter: function(frame) {
                return frame.tag === 'p' && !frame.text.trim();
            } //removes empty p tags  generated by ckeditor...

          });
    return clean;
  }


  handleClick(ref, e) {
    e.preventDefault();
    this.props.onRefClick(ref);
  }

  render() {
    var sources = this.props.sources.length ? this.props.sources.map(function(source, i) {

      if ("ref" in source) {
        return (
          <SheetSource
            key={i}
            source={source}
            sourceNum={i + 1}
            handleClick={this.handleClick}
            cleanHTML={this.cleanHTML}
            onSegmentClick={this.props.onSegmentClick}
          />
        )
      }

      else if ("comment" in source) {
        return (
          <SheetComment
            key={i}
            sourceNum={i + 1}
            source={source}
            cleanHTML={this.cleanHTML}
            onSegmentClick={this.props.onSegmentClick}
          />
        )
      }

      else if ("outsideText" in source) {
        return (
          <SheetOutsideText
            key={i}
            sourceNum={i + 1}
            source={source}
            cleanHTML={this.cleanHTML}
            onSegmentClick={this.props.onSegmentClick}
          />
        )
      }

      else if ("outsideBiText" in source) {
        return (
          <SheetOutsideBiText
            key={i}
            sourceNum={i + 1}
            source={source}
            cleanHTML={this.cleanHTML}
            onSegmentClick={this.props.onSegmentClick}
          />
        )
      }

      else if ("media" in source) {
        return (
          <SheetMedia
            key={i}
            sourceNum={i + 1}
            source={source}
            onSegmentClick={this.props.onSegmentClick}
          />
        )
      }

    }, this) : null;


    return (
      <div className="sheetContent">
        <div className="textInner">{sources}</div>
      </div>
    )
  }
}

class SheetSource extends Component {
  sheetSourceClick(event) {
    this.props.onSegmentClick(this.props.source);
  }


  render() {
    return (
      <div className="sheetItem segment">
        <div className="segmentNumber sheetSegmentNumber sans">
          <span className="en"> <span className="segmentNumberInner">{this.props.sourceNum}</span> </span>
          <span className="he"> <span
            className="segmentNumberInner">{Sefaria.hebrew.encodeHebrewNumeral(this.props.sourceNum)}</span> </span>
        </div>

        {this.props.source.text ?
          <div className="en">
            <div className="ref"><a href={"/" + this.props.source.ref} onClick={(e) => {
              this.props.handleClick(this.props.source.ref, e)
            } }>{this.props.source.ref}</a></div>
            <span dangerouslySetInnerHTML={ {__html: (this.props.cleanHTML(this.props.source.text.en))} } onClick={this.sheetSourceClick}></span>
          </div> : null }

        {this.props.source.text ?
          <div className="he">
            <div className="ref"><a href={"/" + this.props.source.ref} onClick={(e) => {
              this.props.handleClick(this.props.source.ref, e)
            } }>{this.props.source.heRef}</a></div>
            <span dangerouslySetInnerHTML={ {__html: (this.props.cleanHTML(this.props.source.text.he))} } onClick={this.sheetSourceClick}></span>
          </div> : null }


        <div className="clearFix"></div>

      </div>
    )
  }
}

class SheetComment extends Component {
  sheetSourceClick(event) {
    this.props.onSegmentClick(this.props.source);
  }

  render() {
    var lang = Sefaria.hebrew.isHebrew(this.props.source.comment.stripHtml()) ? "he" : "en";
    return (
      <div className="sheetItem segment" onClick={this.sheetSourceClick}>
        <div className="segmentNumber sheetSegmentNumber sans">
          <span className="en"> <span className="segmentNumberInner">{this.props.sourceNum}</span> </span>
          <span className="he"> <span
            className="segmentNumberInner">{Sefaria.hebrew.encodeHebrewNumeral(this.props.sourceNum)}</span> </span>
        </div>
        <div className={lang}>
            <span dangerouslySetInnerHTML={ {__html: this.props.cleanHTML(this.props.source.comment)} }></span>
        </div>
        <div className="clearFix"></div>
      </div>
    )
  }
}

class SheetOutsideText extends Component {
  sheetSourceClick(event) {
    this.props.onSegmentClick(this.props.source);
  }

  render() {
    var lang = Sefaria.hebrew.isHebrew(this.props.source.outsideText.stripHtml()) ? "he" : "en";
    return (
      <div className="sheetItem segment" onClick={this.sheetSourceClick}>
        <div className="segmentNumber sheetSegmentNumber sans">
          <span className="en"> <span className="segmentNumberInner">{this.props.sourceNum}</span> </span>
          <span className="he"> <span
            className="segmentNumberInner">{Sefaria.hebrew.encodeHebrewNumeral(this.props.sourceNum)}</span> </span>
        </div>

        <div className={lang}>
            <span dangerouslySetInnerHTML={ {__html: this.props.cleanHTML(this.props.source.outsideText)} }></span>
        </div>
        <div className="clearFix"></div>

      </div>
    )
  }
}

class SheetOutsideBiText extends Component {
  sheetSourceClick(event) {
    this.props.onSegmentClick(this.props.source);
  }

  render() {
    return (
      <div className="sheetItem segment" onClick={this.sheetSourceClick}>
        <div className="segmentNumber sheetSegmentNumber sans">
          <span className="en"> <span className="segmentNumberInner">{this.props.sourceNum}</span> </span>
          <span className="he"> <span
            className="segmentNumberInner">{Sefaria.hebrew.encodeHebrewNumeral(this.props.sourceNum)}</span> </span>
        </div>

        <div className="en" dangerouslySetInnerHTML={ {__html: this.props.cleanHTML(this.props.source.outsideBiText.en)} }></div>
        <div className="he" dangerouslySetInnerHTML={ {__html: this.props.cleanHTML(this.props.source.outsideBiText.he)} }></div>
        <div className="clearFix"></div>

      </div>
    )
  }

}

class SheetMedia extends Component {
  sheetSourceClick(event) {
    this.props.onSegmentClick(this.props.source);
  }

  makeMediaEmbedLink(mediaURL) {
    var mediaLink;

    if (mediaURL.match(/\.(jpeg|jpg|gif|png)$/i) != null) {
      mediaLink = '<img class="addedMedia" src="' + mediaURL + '" />';
    }

    else if (mediaURL.toLowerCase().indexOf('youtube') > 0) {
      mediaLink = '<iframe width="560" height="315" src=' + mediaURL + ' frameborder="0" allowfullscreen></iframe>'
    }

    else if (mediaURL.toLowerCase().indexOf('soundcloud') > 0) {
      mediaLink = '<iframe width="100%" height="166" scrolling="no" frameborder="no" src="' + mediaURL + '"></iframe>'
    }

    else if (mediaURL.match(/\.(mp3)$/i) != null) {
      mediaLink = '<audio src="' + mediaURL + '" type="audio/mpeg" controls>Your browser does not support the audio element.</audio>';
    }

    else {
      mediaLink = 'Error loading media...';
    }

    return mediaLink
  }

  render() {
    return (
      <div className="sheetItem segment" onClick={this.sheetSourceClick}>
        <div className="segmentNumber sheetSegmentNumber sans">
          <span className="en"> <span className="segmentNumberInner">{this.props.sourceNum}</span> </span>
          <span className="he"> <span
            className="segmentNumberInner">{Sefaria.hebrew.encodeHebrewNumeral(this.props.sourceNum)}</span> </span>
        </div>
        <div dangerouslySetInnerHTML={ {__html: this.makeMediaEmbedLink(this.props.source.media)} }></div>
        <div className="clearFix"></div>

      </div>

    )
  }
}


module.exports = Sheet;
