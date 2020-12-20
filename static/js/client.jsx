import $ from './sefaria/sefariaJquery';
import React from 'react';
import ReactDOM from 'react-dom';
import DjangoCSRF from './lib/django-csrf';
const SefariaReact = require('./ReaderApp');


$(function() {
  var container = document.getElementById('s2');
  var loadingPlaceholder = document.getElementById('appLoading');
  var footerContainer = document.getElementById('footerContainer');
  var component;
  DjangoCSRF.init();
  var renderFunc = ReactDOM.hydrate;
  if (loadingPlaceholder){
    renderFunc = ReactDOM.render;
  }
  Sefaria.unpackDataFromProps(DJANGO_VARS.props);
  if (DJANGO_VARS.inReaderApp) {
    // Rendering a full ReaderApp experience
    component = React.createElement(SefariaReact.ReaderApp, DJANGO_VARS.props);
    renderFunc(component, container);

  } else {
    // Rendering the Header & Footer only on top of a static page
    let staticProps = {
      multiPanel: $(window).width() > 600,
      headerMode: true,
      initialRefs: [],
      initialFilter: [],
      initialMenu: null,
      initialQuery: null,
      initialSheetsTag: null,
      initialNavigationCategories: [],
      initialNavigationTopicCategory: "",
      initialPanels: [],
    };
    let mergedStaticProps = { ...DJANGO_VARS.props, ...staticProps };
    component = React.createElement(SefariaReact.ReaderApp, mergedStaticProps);
    renderFunc(component, container);
    if (footerContainer){
      renderFunc(React.createElement(SefariaReact.Footer), footerContainer);
    }
  }

  if (DJANGO_VARS.containerId && DJANGO_VARS.reactComponentName) {
    // Render a specifc component to a container
    container = document.getElementById(DJANGO_VARS.containerId);
    component = React.createElement(SefariaReact[DJANGO_VARS.reactComponentName], DJANGO_VARS.props);
    renderFunc(component, container);
  }

});
