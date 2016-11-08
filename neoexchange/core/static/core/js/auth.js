/* globals $ rivetsBindings rivets apiRoot refreshTable */
'use strict';
var profile = {
  username: ''
};

var apiRoot = 'https://archive-api.lco.global/';

// rivets.bind($('#profile'), profile);

$.ajaxPrefilter(function(options, originalOptions, jqXHR){
  if(options.url.indexOf('lco.global/') >= 0 && localStorage.getItem('token')){
    jqXHR.setRequestHeader('Authorization', 'Token ' + localStorage.getItem('token'));
  }
});

function getProposals(){
  $.getJSON(apiRoot + 'profile/', function(data){
    profile.username = data.username || '';
  });
}

function login(username, password, callback){
  $.post(
    apiRoot + 'api-token-auth/',
    {
      'username': username,
      'password': password
    }
  ).done(function(data){
    localStorage.setItem('token', data.token);
    getProposals();
    callback(true);
  }).fail(function(){
    callback(false);
  });
}

function logout(){
  localStorage.removeItem('token');
  profile.username = '';
}

$(document).ready(function(){


$('#logout-btn').click(function(){
  logout();
});

$('.alert .close').on('click', function(){
    $(this).parent().hide();
});
});
