var server_url = window.location.href;

function methodClicked() {
	var value;

	if (document.getElementById('MethodToken').checked) {
		value = false;
	}
	else{
		value = true;
	}

	document.getElementById('Token').disabled = value;
	document.getElementById('Login_ID').disabled = !value;
	document.getElementById('Password').disabled = !value;
}

function refresh() {
	ajaxDo('refresh', 'get', null, refreshHandler);
}

function login() {
	var url = document.getElementById('ServerURL').value;
	var protocol = "HTTPS"
	var token = document.getElementById('Token').value;
	var login_id = document.getElementById('Login_ID').value;
	var password = document.getElementById('Password').value;
	var reply_interval = document.getElementById('ReplyInterval').value;
	var max_reply_interval = document.getElementById('MaxReplyInterval').value;
	var reply_message = document.getElementById('ReplyMessage').value;
	var extend_message = document.getElementById('ExtendMessage').value;

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
					 "'extend_message': '" + extend_message + "'}}";

	alert(login_data);
	ajaxDo('login', 'post', login_data, loginHandler);
}

function applyConfig() {
	var reply_interval = document.getElementById('ReplyInterval').value;
	var max_reply_interval = document.getElementById('MaxReplyInterval').value;
	var reply_message = document.getElementById('ReplyMessage').value;
	var extend_message = document.getElementById('ExtendMessage').value;

	var config_data = "{'reply_config': {" +
					  "'reply_interval': '" + reply_interval + "', " +
					  "'max_reply_interval': '" + max_reply_interval + "', " +
					  "'reply_message': '" + reply_message + "', " +
					  "'extend_message': '" + extend_message + "'}}";

	alert(config_data);
	ajaxDo('apply_config', 'post', config_data, applyConfigHandler);
}

function refreshHandler(data) {
	var json = JSON.parse(data);

	document.getElementById('ServerURL').value = json.url;
	document.getElementById('HTTP').checked = (json.protocol == 'HTTP');
	document.getElementById('HTTPS').checked = !(json.protocol == 'HTTP');
	document.getElementById('MethodToken').checked = !(json.token == '');
	document.getElementById('MethodPassword').checked = (json.token == '');
	document.getElementById('Token').value = json.token;
	document.getElementById('Login_ID').value = json.login_id;
	document.getElementById('Password').value = json.password;
	document.getElementById('ReplyInterval').value = json.reply_config.reply_interval;
	document.getElementById('MaxReplyInterval').value = json.reply_config.max_reply_interval;
	document.getElementById('ReplyMessage').value = json.reply_config.reply_message;
	document.getElementById('ExtendMessage').value = json.reply_config.extend_message;

	methodClicked();

	if (json.work_status == 1) {
		document.getElementById('ConnectStatus').innerHTML = 'Working';
		document.getElementById('ConnectStatus').style.color = 'green';
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
		document.getElementById('ConnectStatus').innerHTML = 'Not connected';
		document.getElementById('ConnectStatus').style.color = 'red';
	}
}

function loginHandler(data) {
	var json = JSON.parse(data);

	if (json.result == -1)
		alert('Login failed.');
	else
		alert('Login successed.')

	location.reload();
}

function applyConfigHandler(data) {
	var json = JSON.parse(data);

	if (json.result == -1)
		alert('Apply config failed.');
	else
		alert('Apply config successed.')

	location.reload();
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