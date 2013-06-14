url_split = document.URL.split('/');
conf_id = url_split[url_split.length - 1];
// twisted_django_server/twisted_django.js
sock = function(debug, wsuri, disable_authentication) {
    window.WEB_SOCKET_DEBUG = true;
    window.WEB_SOCKET_SWF_LOCATION ="/static/web-socket/WebSocketMain.swf";
    function close_websocket() {
        console.log('closing websocket!');
        sock.close();
    }
    $(window).on('beforeunload', close_websocket);
    var sock = {};
    var listeners = {};
    var init_funcs = [];
    var connected = false;
    var authenticated = false;
    var ready = false;

    if(typeof(disable_authentication) === 'undefined') {
        disable_authentication = false;
    }
    
    //Initialization stuff
    ellog = document.getElementById('log');
    wsuri = "ws://" + window.location.hostname + ":31415";

    if ("MozWebSocket" in window && TESTING === false) {
        sock = new MozWebSocket(wsuri);
    } else if(TESTING === false) {
        sock = new WebSocket(wsuri);
        if(debug) {
            //console.log("WS-URI", wsuri);
            //console.log("SOCK AFTER CONNECT: " + sock);
        }
    } else if(TESTING === true) {
        sock.send = function(msg) {
            if(typeof(testing_send_queue) === 'undefined') {
                testing_send_queue = [];
            }
            testing_send_queue.append(msg);
        }
    }

    sock.onopen = function() {
        if(debug) {
            //console.log("Connected to " + wsuri);
        }
        connected = true;
        if(disable_authentication === false) {
            authenticateTwistedDjango(return_obj);
        } else {
            for(var i = 0; i < init_funcs.length; i++) {
                init_funcs[i]();
            }
        }
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
        authenticated = false;
        ready = false;
    }

    sock.onmessage = function(e) {
        response = JSON.parse(e.data);
        console.log(e.data);
        var value = null;
        var spent_commands = new Array();
        for(var key in response) {
            if(debug) {
                console.log("%c {0}: ".format(key), 'color: #31c96a' , response);
            }
            if(key === 'authenticate' && disable_authentication === false) {
                if(response[key]['authenticate'] === 'success') {
                    authenticated = true;
                    if(connected === true) {
                        ready = true;
                    }
                    user_name = response[key]['name'];
                    permissions = response[key]['permissions'];
                    for(var i = 0; i < init_funcs.length; i++) {
                        init_funcs[i]();
                    }
                } else {
                    if(response['loginUrl'] !== undefined) {
                        loginUrl = response['loginUrl'];
                        window.location.href = loginUrl
                    }
                }
                return
            }
            commands = listeners[key];
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
                            listeners[key].splice(spent_commands[i], 1);
                        }
                        listeners[key] = commands;
                    }
                    spent_commands = new Array();
                }
            }
        }
    }

    var return_obj = {
        'echo_alert': function(response) {
            alert(response.message);
        },
        'echo_test': function() {
            sock.on('echo_test', echo_alert, false);
            sock.send(JSON.stringify({
                echo_test: {
                    message: "Hello, World!"
                }
            }));
        },
        'is_authenticated': function() {
            return authenticated;
        },
        'is_connected': function() {
            return connected;
        },
        'onready': function(func) {                                                                                                                                                                                     
            if(ready === true) {
                func();
            } else {
                init_funcs.push(func);
            }
        },
        'on': function(key, listener, once) {
            if(debug) {
                //console.log('adding listener key: ', key, ",);
            }   
            if(typeof(listeners) == 'undefined'){
                listeners = {}; 
            }   
            if(typeof(listeners[key]) === 'undefined'){
                listeners[key] = new Array();
            }   
            listeners[key].push({
                'listener':listener, 
                'run_once':once
            });
        },
        'send': function(msg) {
            //console.log('sending: ', msg);
            sock.send(msg);
        }
    };
    return return_obj;
}(true);
