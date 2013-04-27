// connex/twisted_django_server/twisted_django.js
var sock = null;
var ellog = null;
var session_id = null;
var conf_id = "";
var redirectingToLogin = false;
var twistedDebug = true;
window.WEB_SOCKET_DEBUG = true;
window.WEB_SOCKET_SWF_LOCATION ="/static/web-socket/WebSocketMain.swf";

//http://whattheheadsaid.com/2010/10/a-safer-object-keys-compatibility-implementation
if (!Object.keys) {
    Object.keys = Object.keys || (function () {
        var hasOwnProperty = Object.prototype.hasOwnProperty,
            hasDontEnumBug = !{toString:null}.propertyIsEnumerable("toString"),
            DontEnums = [
                'toString',
                'toLocaleString',
                'valueOf',
                'hasOwnProperty',
                'isPrototypeOf',
                'propertyIsEnumerable',
                'constructor'
            ],
            DontEnumsLength = DontEnums.length;

        return function (o) {
            if (typeof o != "object" && typeof o != "function" || o === null)
                throw new TypeError("Object.keys called on a non-object");

            var result = [];
            for (var name in o) {
                if (hasOwnProperty.call(o, name))
                    result.push(name);
            }

            if (hasDontEnumBug) {
                for (var i = 0; i < DontEnumsLength; i++) {
                    if (hasOwnProperty.call(o, DontEnums[i]))
                        result.push(DontEnums[i]);
                }
            }

            return result;
        };
    })();
}

//https://developer.mozilla.org/en-US/docs/JavaScript/Reference/Global_Objects/Array/IndexOf
if (!Array.prototype.indexOf) {
    Array.prototype.indexOf = function (searchElement /*, fromIndex */ ) {
        "use strict";
        if (this === null) {
            throw new TypeError();
        }
        var t = Object(this);
        var len = t.length >>> 0;
        if (len === 0) {
            return -1;
        }
        var n = 0;
        if (arguments.length > 1) {
            n = Number(arguments[1]);
            if (n != n) { // shortcut for verifying if it's NaN
                n = 0;
            } else if (n !== 0 && n != Infinity && n != -Infinity) {
                n = (n > 0 || -1) * Math.floor(Math.abs(n));
            }
        }
        if (n >= len) {
            return -1;
        }
        var k = n >= 0 ? n : Math.max(len - Math.abs(n), 0);
        for (; k < len; k++) {
            if (k in t && t[k] === searchElement) {
                return k;
            }
        }
        return -1;
    };
}

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
            //echo_test();
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
            //loadParticipants(undefined);
            //updateTable(undefined);
            
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

function echo_test() {
    sock.registerListener('echo_test', echo_alert, false);
    sock.send(JSON.stringify({echo_test: {message: "Hello, World!"}}));
}

function echo_alert(response) {
    alert(response.message);
}

function authenticateTwistedDjango() {
    var url_split = document.URL.split('/');

    $.ajax({ type:'GET',
             url:'/accounts/session_id',
             async:false,
             success:function(text){session_id = text;}
           });
    authentication_obj = {'authenticate':session_id};
    if(sock != null) {
        sock.send(JSON.stringify(authentication_obj));
    }
    sock.registerListener('authenticate', authenticated, true);

    //make sure to clean up the socket when finished
    $(window).unload(function() {
        if(sock !== null) {
            sock.close();
        }
    });
}

function authenticated(response) {
    if (response.authenticate === "success") {
        alert("Authenticated!");
    } else {
        authenticationFailed();
    }
}

function authenticationFailed() {
    alert("Authentication Failed");
}

$(document).ready(function() {
    $('#connex_global_error').hide();
});
