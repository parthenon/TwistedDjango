function authenticateTwistedDjango() {
    var url_split = document.URL.split('/');

    $.ajax({ 
        type:'GET',
        url:'/accounts/session_id',
        async:false,
        success:function(text){session_id = text;}
   });
    authentication_obj = {
        'authenticate':session_id
    };
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
