var server_url = window.location.href;

function methodClicked() {
	var value;

	if (document.getElementById('MethodToken').checked) {
		value = false;
		document.getElementById('Login_ID').value = '';
		document.getElementById('Password').value = '';
	}
	else{
		value = true;
		document.getElementById('Token').value = '';
	}

	document.getElementById('Token').disabled = value;
	document.getElementById('Login_ID').disabled = !value;
	document.getElementById('Password').disabled = !value;
}

function refresh() {
	ajaxDo('refresh', 'get', null, refreshHandler);
}

function login() {
	var url = document.getElementById('ServerURL').value.replaceAll("'", "\\'");
	var protocol = "HTTPS"
	var token = document.getElementById('Token').value.replaceAll("'", "\\'");
	var login_id = document.getElementById('Login_ID').value.replaceAll("'", "\\'");
	var password = document.getElementById('Password').value.replaceAll("'", "\\'");
	var reply_interval = document.getElementById('ReplyInterval').value.replaceAll("'", "\\'");
	var max_reply_interval = document.getElementById('MaxReplyInterval').value.replaceAll("'", "\\'");
	var reply_message = document.getElementById('ReplyMessage').innerText.replaceAll("'", "\\'");
	var extend_message = document.getElementById('ExtendMessage').value.replaceAll("'", "\\'");
	var whitelist = document.getElementById('WhiteList').value.replaceAll("'", "\\'");

	if (reply_interval == '' || max_reply_interval == '') {
		alert("reply_interval and max_reply_interval is required.")
		return;
	}

	if (document.getElementById('HTTP').checked)
		protocol = "HTTP"

	var login_data = "{'url': '" + url + "', " +
					 "'protocol': '" + protocol + "', " +
					 "'token': '" + token + "', " +
					 "'login_id': '" + login_id + "', " +
					 "'password': '" + password + "', " +
					 "'reply_config': {" +
					 "'reply_interval': '" + reply_interval + "', " +
					 "'max_reply_interval': '" + max_reply_interval + "', " +
					 "'reply_message': '" + reply_message + "', " +
					 "'extend_message': '" + extend_message + "', " +
					 "'whitelist': '" + whitelist + "'}}";

	login_data = login_data.replaceAll("\n", "\\n");

	ajaxDo('login', 'post', login_data, loginHandler);
}

function applyConfig() {
	var reply_interval = document.getElementById('ReplyInterval').value.replaceAll("'", "\\'");
	var max_reply_interval = document.getElementById('MaxReplyInterval').value.replaceAll("'", "\\'");
	var reply_message = document.getElementById('ReplyMessage').innerText.replaceAll("'", "\\'");
	var extend_message = document.getElementById('ExtendMessage').value.replaceAll("'", "\\'");
	var whitelist = document.getElementById('WhiteList').value.replaceAll("'", "\\'");

	var config_data = "{'reply_config': {" +
					  "'reply_interval': '" + reply_interval + "', " +
					  "'max_reply_interval': '" + max_reply_interval + "', " +
					  "'reply_message': '" + reply_message + "', " +
					  "'extend_message': '" + extend_message + "', " +
					  "'whitelist': '" + whitelist + "'}}";

	config_data = config_data.replaceAll("\n", "\\n");

	ajaxDo('apply_config', 'post', config_data, applyConfigHandler);
}

function refreshHandler(data) {
	var json = JSON.parse(data);

	if (json.url != "undefined")
		document.getElementById('ServerURL').value = json.url;
	document.getElementById('HTTP').checked = (json.protocol == 'HTTP');
	document.getElementById('HTTPS').checked = !(json.protocol == 'HTTP');
	document.getElementById('MethodToken').checked = !(json.token == '' || json.token == 'undefined');
	document.getElementById('MethodPassword').checked = (json.token == '' || json.token == 'undefined');

	if (json.token != "undefined")
		document.getElementById('Token').value = json.token;
	if (json.login_id != "undefined")
		document.getElementById('Login_ID').value = json.login_id;
	if (json.password != "undefined")
		document.getElementById('Password').value = json.password;
	document.getElementById('ReplyInterval').value = json.reply_config.reply_interval;
	document.getElementById('MaxReplyInterval').value = json.reply_config.max_reply_interval;
	document.getElementById('ReplyMessage').innerText = json.reply_config.reply_message;
	document.getElementById('ExtendMessage').value = json.reply_config.extend_message;
	document.getElementById('WhiteList').value = json.reply_config.whitelist;

	methodClicked();

	if (json.work_status == 1) {
		document.getElementById('ConnectStatus').innerText = 'Working';
		document.getElementById('ConnectStatusRadio').checked = true;
		document.getElementById('ServerURL').disabled = true;
		document.getElementById('HTTP').disabled = true;
		document.getElementById('HTTPS').disabled = true;
		document.getElementById('MethodToken').disabled = true;
		document.getElementById('MethodPassword').disabled = true;
		document.getElementById('Token').disabled = true;
		document.getElementById('Login_ID').disabled = true;
		document.getElementById('Password').disabled = true;
		document.getElementById('Login').disabled = true;
	}
	else {
		document.getElementById('ConnectStatus').innerText = 'Not connected';
		document.getElementById('ConnectStatusRadio').checked = false;
	}
}

function loginHandler(data) {
	var json = JSON.parse(data);

	if (json.result == -1) {
		alert('Login failed.');
	}
	else {
		alert('Login successed.')
		location.reload();
	}

}

function applyConfigHandler(data) {
	var json = JSON.parse(data);

	if (json.result == -1) {
		alert('Apply config failed.');
	}
	else {
		alert('Apply config successed.')
		location.reload();
	}

}

function ajaxObject() {
	var xmlHttp;
	try {
		// Firefox, Opera 8.0+, Safari
		xmlHttp = new XMLHttpRequest();
	}
	catch (e) {
		// Internet Explorer
		try {
			xmlHttp = new ActiveXObject("Msxml2.XMLHTTP");
		} catch (e) {
			try {
				xmlHttp = new ActiveXObject("Microsoft.XMLHTTP");
			} catch (e) {
				alert("Ajax is not supported");
				return false;
			}
		}
	}
	return xmlHttp;
}

function ajaxDo(api, method, data, callback) {
	var ajax = ajaxObject();
	ajax.timeout = 10000;
	ajax.open(method , server_url + api , true);
	ajax.setRequestHeader("Content-Type" , "application/x-www-form-urlencoded");
	ajax.onreadystatechange = function () {
		if (ajax.readyState == 4 && ajax.status == 200) {
			callback(ajax.responseText);
 		}
	}
	ajax.send(data);
}