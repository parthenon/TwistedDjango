// connex/twisted_django_server/twisted_django.js
// jslint browser: true

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

sock = function(wsuri, debug) {
    window.WEB_SOCKET_DEBUG = true;
    window.WEB_SOCKET_SWF_LOCATION ="/static/web-socket/WebSocketMain.swf";
    
    var sock;
    var listeners = {};
    var init_funcs = [];
    var connected = false;
    var auth_func = function() {
        return false;
    }
    var authenticated = false;
    
    //Initialization stuff
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
        if(debug) {
            console.log("WS-URI", wsuri);
            console.log("SOCK AFTER CONNECT: " + sock);
        }
    }
    sock.onopen = function() {
        if(debug) {
            console.log("Connected to " + wsuri);
        }

        authenticateTwistedDjango();
        connected = true;
    }
    sock.onclose = function(e) {
        if(debug) {
            console.log("Connection closed (wasClean = " + 
                        e.wasClean + 
                        ", code = " + 
                        e.code + 
                        ", reason = '" + 
                        e.reason + "')");
        }
        connected = false;
    }
    sock.onmessage = function(e) {
        response = JSON.parse(e.data);
        if(debug) {
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

    return {
        echo_alert: function(response) {
            alert(response.message);
        },
        echo_test: function() {
            sock.registerListener('echo_test', echo_alert, false);
            sock.send(JSON.stringify({
                echo_test: {
                    message: "Hello, World!"
                }
            }));
        },
        is_authenticated = function() {
            return authenticated;
        },
        is_connected = function() {
            return connected;
        },
        onready = function(func) {
            init_funcs.push(func);
        },
        on = function(key, listener, once) {
            if(debug) {
                console.log('adding listener: ', key);
            }   
            if(typeof(listeners) == 'undefined'){
                listeners = {}; 
            }   
            if(typeof(sock.listeners[key]) == 'undefined'){
                sock.listeners[key] = new Array();
            }   
            sock.listeners[key].push({
                'listener':listener, 
                'run_once':once
            });
        },
    }
});
