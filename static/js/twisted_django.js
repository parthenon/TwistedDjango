var sock = {};
var ellog = null;
var session_id = null;
var redirectingToLogin = false;

window.WEB_SOCKET_DEBUG = true;
var printNewData = false;

console.log('Initializing socket');

window.WEB_SOCKET_SWF_LOCATION ="/static/web-socket/WebSocketMain.swf";
ellog = document.getElementById('log');

if (window.location.protocol === "file:") {
    wsuri = "ws://127.0.0.1:31415";
} else {
    wsuri = "ws://" + window.location.hostname + ":31415";
}

if ("MozWebSocket" in window) {
    sock = new MozWebSocket(wsuri);
} else {
    sock = new WebSocket(wsuri);
    if(window.WEB_SOCKET_DEBUG) {
        console.log("WS-URI", wsuri);
        console.log("SOCK AFTER CONNECT: " + sock);
    }
}

console.log(wsuri);

sock.listeners = {};
sock.initFuncs = [];
sock.connected = false;
sock.state = 'Initializing connection.';

sock.onopen = function() {
    if(window.WEB_SOCKET_DEBUG) {
        console.log("Connected to " + wsuri);
    }
    sock.state = 'Authenticating.';
    
    //Authenticate the connection against the website
    sock.authenticate(function(response) {
        //TODO: finish this function
        state = 'Authentication failed';
        console.log('Authentication failed');
        return;
    });

    sock.state = 'Authenticated'
    sock.connected = true;
    for(var i = 0; i < this.initFuncs.length; i++) {
        this.initFuncs[i]();
    }
}
sock.onclose = function(e) {
    if(window.WEB_SOCKET_DEBUG) {
        console.log("Connection closed (wasClean = " + 
                    e.wasClean + 
                    ", code = " + 
                    e.code + 
                    ", reason = '" + 
                    e.reason + "')");
    }
    sock.connected = false;
    sock.state = 'Disconnected: ' + e.reason;
}
sock.onmessage = function(e) {
    response = JSON.parse(e.data);
    if(window.WEB_SOCKET_DEBUG) {
        if(response['new_data_point'] === undefined || printNewData === true) {
            console.log("Response: ", response);
        }
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
sock.onready = function(func) {
    this.initFuncs.push(func);
};
sock.on = function(key, listener, once) {
    if(window.WEB_SOCKET_DEBUG) {
        console.log('adding listener: ', key);
    }
    if(typeof(this.listeners) == 'undefined'){
        this.listeners = {};
    }
    if(typeof(this.listeners[key]) == 'undefined'){
        this.listeners[key] = new Array();
    }
    this.listeners[key].push({'listener':listener, 'run_once':once});
};
sock.isConnected = function() {
    return sock.connected;
}


sock.authenticate = function(callback) {
    var url_split = document.URL.split('/');
    //sock.send(JSON.stringify({'get_available_sets': {}}));

    //$.ajax({ type:'GET',
    //         url:'/accounts/session_id',
    //         async:false,
    //         success:function(text){session_id = text;}
    //       });
    //authentication_obj = {'authenticate':session_id};
    //if(sock != null) {
    //    sock.send(JSON.stringify(authentication_obj));
    //}
    //authenticate_user = {'authenticate_user': {'':conf_id}}
    //if(sock != null) {
    //    sock.send(JSON.stringify(authenticate_user));
    //}
    //sock.registerListener('authenticate', authenticated, true);

    //make sure to clean up the socket when finished

    $(window).unload(function() {
        sock.close();
    });
}


