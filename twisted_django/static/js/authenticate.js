function authenticateTwistedDjango(on_authentication_response) {
    var url_split = document.URL.split('/');

    $.ajax({ 
        type:'GET',
        url:'/accounts/session_id/',
        async:false,
        cache:false,
        success:function(text){ 
            session_id = text; 
            authentication_obj = {
                'authenticate': {
                    'session_id': session_id
                }
            };

            sock.send(JSON.stringify(authentication_obj));
        }
    });
}
