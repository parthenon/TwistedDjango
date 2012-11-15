// connex/twisted_django_server/twisted_django.js
var sock = null;
var ellog = null;
var session_id = null;
var conf_id = "";
var redirectingToLogin = false;
var twistedDebug = true;
window.WEB_SOCKET_DEBUG = true;
window.WEB_SOCKET_SWF_LOCATION ="/static/web-socket/WebSocketMain.swf";

$( function() {
    var wsuri;
    ellog = document.getElementById('log');
    if (window.location.protocol === "file:") {
        wsuri = "ws://192.168.1.135:8080";
    } else {
        wsuri = "ws://" + window.location.hostname + ":31415";
    }
    if ("MozWebSocket" in window) {
        sock = new MozWebSocket(wsuri);
    } else {
        sock = new WebSocket(wsuri);
        if(twistedDebug) {
            console.log("WS-URI", wsuri);
            console.log("SOCK AFTER CONNECT: " + sock);
        }
    }
    if (sock) {
        sock.listeners = {};
        sock.onopen = function() {
            if(twistedDebug) {
                console.log("Connected to " + wsuri);
            }
            authenticateTwistedDjango();
        }
        sock.onclose = function(e) {
            if(twistedDebug) {
                console.log("Connection closed (wasClean = " + 
                            e.wasClean + 
                            ", code = " + 
                            e.code + 
                            ", reason = '" + 
                            e.reason + "')");
            }
            sock = null;
            $('#connex_global_error').text('The connection has been closed').show();
            loadParticipants(undefined);
            updateTable(undefined);
            
        }
        sock.onmessage = function(e) {
            response = JSON.parse(e.data);
            if(twistedDebug) {
                console.log("Response: ", response);
            }
            var value = null;
            var spent_commands = new Array();
            for (var key in response) {
                commands = this.listeners[key];
                if(typeof commands === 'undefined') {
                    continue;
                } else {
                    if(commands.length > 0) {
                        for(var i = 0;i < commands.length;i++) {
                            commands[i]['listener'](response[key]);
                            if(commands[i]['run_once'] === true) {
                                spent_commands.push(i);
                            }
                        }
                        if(spent_commands.length > 0) {
                            for(var i = spent_commands.length; i >= 0; i--) {
                                this.listeners[key].splice(spent_commands[i], 1);
                            }
                            this.listeners[key] = commands;
                        }
                        spent_commands = new Array();
                    }
                }
            }
        }
        sock.registerListener = function(key, listener, once) {
            if(twistedDebug) {
                console.log('adding listener: ', key);
            }
            if(typeof this.listeners == 'undefined'){
                this.listeners = {};
            }
            if(typeof this.listeners[key] == 'undefined'){
                this.listeners[key] = new Array();
            }
            this.listeners[key].push({'listener':listener, 'run_once':once});
        }
    }
});

function authenticateTwistedDjango() {
    var url_split = document.URL.split('/');
    conf_id = url_split[url_split.length - 1];

    $.ajax({ type:'GET',
             url:'/accounts/session_id',
             async:false,
             success:function(text){session_id = text;}
           });
    authentication_obj = {'authenticate':session_id};
    if(sock != null) {
        sock.send(JSON.stringify(authentication_obj));
    }
    authenticate_user = {'authenticate_user': {'conf_id':conf_id}}
    if(sock != null) {
        sock.send(JSON.stringify(authenticate_user));
    }
    sock.registerListener('authenticate', authenticated, true);

    //make sure to clean up the socket when finished
    $(window).unload(function() {
        if(sock !== null) {
            sock.close();
        }
    });
}

function authenticated(response_val) {
    if('error' in response_val) {
        $('#connex_global_error').text('Authentication failed! Trying again in: 5').show();
        authSecondsElapsed = 0;
        authRetryIntervalId = window.setInterval(authenticationFailed, 5000);
        return;
    } else {
        $('#connex_global_error').text('').hide();
    }
    
    if(typeof(connectToChat) !== 'undefined')
        connectToChat(response_val);
    if(typeof(initParticipants) !== 'undefined')
        initParticipants(response_val);
    if(typeof(initMisc) !== 'undefined')
        initMisc(response_val);
    if(typeof(initQuestions) !== 'undefined')
        initQuestions(response_val);
    if(typeof(initWhosOnline) !== 'undefined')
        initWhosOnline(response_val);
}

function authenicationFailed() {
    authSecondsElapsed += 1;
    if(authSecondsElapsed === 5) {
        window.clearInterval(authRetryIntervalId);
        authentication_obj = {'authenticate':session_id};
        if(sock != null) {
            sock.send(JSON.stringify(authentication_obj));
        }
        $('#connex_global_error').hide();
    } else {
        $('#connex_global_error').text('Authentication failed! Trying again in: ' + 
                                       (5 - authSecondsElapsed) ).show();
        authRetryIntervalId = window.setInterval(authenticationFailed, 5000);
    }
}

$(document).ready(function() {
    $('#connex_global_error').hide();
});
