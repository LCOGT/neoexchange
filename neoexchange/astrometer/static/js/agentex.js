// Elements with the class "accessible" are intended for people who don't 
// have Javascript enabled. If we are here they obviously do have Javascript.
document.write('<style type="text/css"> .accessible { display: none; }</style>');

// Requires jQuery to be loaded.
var showhelp = false;

function addHelpHint(el,msg,align,talign){
	// Check for existence of the style "helpityhint". If it doesn't exist, we provide a default
	if($("style:contains('.helpityhint')").length < 1) $("head").append("<style type='text/css'> .helpityhint { box-shadow: 0px 0px 8px rgb(255,0,0)!important; -moz-box-shadow: 0px 0px 8px rgb(255,0,0)!important; -webkit-box-shadow: 0px 0px 8px rgb(255,0,0)!important; cursor: help!important; z-index: 20; } <\/style>");
	// Attach our message as data and attach mouse events
	el.data('help',msg).bind('mouseover',function(e){
		if(showhelp){
			$(this).addClass('helpityhint');
			bubblePopup({id:'helptooltip',el:$(this),html:$(this).data('help'),'padding':10,'align':align,'textalign':talign,z:20});
		}
	}).bind('mouseout',function(){
		if(showhelp){
			$(this).removeClass('helpityhint');
			// We need to allow people to click on links in the help tool tip
			// Give them 1s to get to it and cancel the fadeOut. Then they 
			// can click to hide it.
			$('#helptooltip').bind('mouseover',function(){ $(this).clearQueue(); }).bind('click',function(){ $(this).hide(); });
			$('#helptooltip').delay(1000).fadeOut(500);
		}
	});
}

function defaultColours(){
	colours = { source: {text:"",bg:""},sky: {text:"",bg:""},calibrator: {text:"",bg:""} }
	for(var i = 0; i < document.styleSheets.length; i++) {
		try{
			var sheet = document.styleSheets[i];
			rules = sheet.rules||sheet.cssRules;
			if(rules){
				for(var j = 0; j < rules.length; j++) {
					if(rules[j].selectorText){
						if(rules[j].selectorText.toLowerCase()==".source") colours.source = {bg:stripOpacity(rules[j].style.backgroundColor),text:rules[j].style.color};
						if(rules[j].selectorText.toLowerCase()==".calibrator") colours.calibrator = {bg:stripOpacity(rules[j].style.backgroundColor),text:rules[j].style.color};
						if(rules[j].selectorText.toLowerCase()==".sky") colours.sky = {bg:stripOpacity(rules[j].style.backgroundColor),text:rules[j].style.color};
					}
				}
			}
		}catch(e){
			// If we can't access the stylesheet (probably because it is on another domain) do nothing!
		};
	}
	return colours;
}

function stripOpacity(c){
	if(c.indexOf("rgba") != 0) return c;
	var rgb = c.substring(c.indexOf("(")+1,c.length).split(",");
	return 'rgb('+rgb[0]+','+rgb[1]+','+rgb[2]+')';
}

function unixtohours(timestamp){
	var date = new Date(timestamp);
	// hours part from the timestamp
	var hours = date.getUTCHours();
	// minutes part from the timestamp
	var minutes = date.getUTCMinutes();
	if (hours <=9) hours = "0"+hours;
	if (minutes <= 9 ) minutes = "0"+minutes;
	return hours+":"+minutes;
}

function toggleHelp(el){
	showhelp = !showhelp;
	if(!showhelp){
		$('.helpityhint').removeClass('helpityhint')
		$(el).removeClass('helpactive');
		$('#helptooltip').remove()
	}else{
		$(el).addClass('helpactive');
		msg = ($('#help').html()) ? $('#help').html() : 'Move your mouse over different parts of the page to see specific help.'
		bubblePopup({id:'helptooltip',el:$(el),w:200, align:'left',html:msg,'padding':10,dismiss:true});
	}
	return false;
}

function positionHelperLinks(){
	var tp = 70;
	var p = $('.page').position();
	var top = p.top + tp;
	var tall = $('#mylink').outerHeight();
	var padd = parseInt($('.page').css('padding-right'))/2;
	var l = p.left+$('.page').outerWidth()+padd;
	$('#helplink').css({position:'absolute',left:l,top:(top-tall-5)});
	$('.tablink').css({position:'absolute',left:l})
	$('#mylink').css({top:top});
	$('#avlink').css({top:top+tall+5});
	$('#sulink').css({top:top+tall+tall+10});
}


$(document).ready(function(){

	// Set up alternatve graph tabs
	if($('#mylink').length > 0){
		var h = '<div id="mylink" class="tablink'+(($('#mylink').hasClass('tabactive')) ? ' tabactive':'')+'">'+$('#mylink').html()+'<\/div>';
		if($('#avlink').length > 0) h += '<div id="avlink" class="tablink'+(($('#avlink').hasClass('tabactive')) ? ' tabactive':'')+'">'+$('#avlink').html()+'<\/div>';
		if($('#sulink').length > 0) h += '<div id="sulink" class="tablink'+(($('#sulink').hasClass('tabactive')) ? ' tabactive':'')+'">'+$('#sulink').html()+'<\/div>';
		$('#mylink').remove();
		$('#avlink').remove();
		$('#sulink').remove();
		$('body #main').append(h);
	}

	if(typeof helper=="boolean" && helper){
		$('body #main').append('<div id="helplink" class="tablink">?<\/div>')
		var p = $('.page').position();
		var tall = $('#helplink').outerHeight();
		$('#helplink').bind('click',function(e){ toggleHelp(this); });
	}

	if($('#mylink').length > 0) positionHelperLinks();

	// Bind resize event - re-position helper links mylink
	if($('#mylink').length > 0) $(window).resize(function(){ positionHelperLinks(); });
	
	$('.fancybtndisable').live('click',function(e){ e.preventDefault(); });

});
