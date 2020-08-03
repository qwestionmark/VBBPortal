import React, { Component } from "react";
import { BrowserRouter } from "react-router-dom";
import { connect } from "react-redux";
import * as actions from "./store/actions/auth";

import Layout from "./components/Layout";
import Routes from "./Routes";
import "./style.css";

class App extends Component {
  componentDidMount() {
    console.log("try auto sign up");
    this.props.onTryAutoSignup();
  }

  render() {
    return (
      <div className="App">
        <BrowserRouter {...this.props}>
          <Layout {...this.props}>
            <Routes />
          </Layout>
        </BrowserRouter>
      </div>
    );
  }
}

const mapStateToProps = (state) => {
  return {
    isAuthenticated: state.token !== null,
    isLoading: state.loading,
  };
};

const mapDispatchToProps = (dispatch) => {
  return {
    onTryAutoSignup: () => dispatch(actions.authCheckState()),
  };
};

export default connect(mapStateToProps, mapDispatchToProps)(App);
