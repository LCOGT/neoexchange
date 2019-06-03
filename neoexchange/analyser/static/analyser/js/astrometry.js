// Astrometry JS library - created by Stuart Lowe for Las Cumbres Observatory 2012
// Adapted by Edward Gomez 2019
//
// Web pages define x,y to start at the top left but FITS is bottom left. The input and output of y will be in FITS definition.
//photo = new Astrometry({id:'photometric',src:"{{data.image}}",form:'entryform',width:width,source:{x:s_x,y:s_y,r:start_r},sky:{x:b_x,y:b_y,r:start_r,label:'Sky'},calibrator:{x:c_x[0],y:c_y[0],r:start_r},zoom:2,callback:photoReady,calibrators:calibrators});

function Astrometry(inp){

	this.im = new Image();
	this.cur = {x:0,y:0};
	this.width;
	this.height;
	this.zoom = 2;
	this.src;
	this.holder = { id:'imageholder', img: 'imageholder_small', zoomed: 'imageholder_big', svg:'svgcanvas' };
	this.svg;
	this.candidates;
	this.candidateszoomed;
	this.calibrator = {r:20,label:'Candidate',callback:''};
	this.sizer = new Array();
	this.img_stack = new Array();
	//this.suggested = new Array();
	//this.suggestedvisible = false;
	this.l = 0;
	this.t = 0;
	this.groupmove = false;
	this.shiftkey = false;

	// Overwrite defaults with variables passed to the function
	if(typeof inp=="object"){
		if(typeof inp.id=="string"){
			this.holder.id = inp.id;
			this.holder.img = inp.id+'_'+this.holder.img;
			this.holder.zoomed = inp.id+'_'+this.holder.zoomed;
			this.holder.svg = inp.id+'_'+this.holder.svg;
		}
		if(typeof inp.src=="string") this.src = inp.src;
		if(typeof inp.width=="number") this.width = inp.width;
		if(typeof inp.height=="number") this.height = inp.height;
		if(typeof inp.zoom=="number") this.zoom = inp.zoom;
		if(typeof inp.calibrator=="object"){
			if(typeof inp.calibrator.r=="number") this.calibrator.r =  inp.calibrator.r;
			if(typeof inp.calibrator.label=="string") this.calibrator.label = inp.calibrator.label;
		}
    if(typeof inp.img_stack=="object") this.img_stack = inp.img_stack;
		if(typeof inp.candidates=="object") this.candidates = inp.candidates;
		//if(typeof inp.suggested=="object") this.suggested = inp.suggested;
		this.form = inp.form;
	}else{
		if(typeof inp=="string") this.src = inp;
	}
	if(typeof inp.callback=="function") this.callback = inp.callback;

	if(this.src){
		// Keep a copy of this so that we can reference it in the onload event
		var _object = this;
		// Define the onload event before setting the source otherwise Opera/IE might get confused
		this.im.onload = function(){ _object.loaded(); if(_object.callback) _object.callback.call(); }
		this.im.src = this.src

		if($('#'+this.holder.id).length==0) $('body').append('<div id="'+this.holder.id+'"></div>');
		if($('#'+this.holder.img).length==0) $('#'+this.holder.id).append('<div id="'+this.holder.img+'"><img src="'+this.src+'" alt="LCOGT image" id ="analyser_image" /></div>');
		if($('#'+this.holder.zoomed).length==0) $('#'+this.holder.id).append('<div id="'+this.holder.zoomed+'" style="display:none;"><img src="'+this.src+'" alt="LCOGT image" id="analyser_image_zoomed" /></div>');
		if($('#'+this.holder.svg).length==0) $('#'+this.holder.id).append('<div id="'+this.holder.svg+'"></div>');

		this.pos = $('#'+this.holder.id).position();
	}
}

// We've loaded the image so now we can proceed
Astrometry.prototype.loaded = function(){

	// Apply width/height depending on what input we have
	if(!this.height && this.width) this.height = this.im.height*this.width/this.im.width;	// Only defined width so work out appropriate height
	if(!this.width && this.height) this.width = this.im.width*this.height/this.im.height;	// Only defined height so work out appropriate width
	if(!this.width) this.width = this.im.width;	// No width defined so get it from the image
	if(!this.height) this.height = this.im.height;	// No height defined so get it from the image

	// Set the zoom level
	this.zoom = Math.ceil(this.im.width/this.width);

	$('#'+this.holder.id).css({'position':'relative','z-index':0,overflow:'hidden','width':this.width,'height':this.height});
	$('#'+this.holder.img).css({'position':'absolute','left':0,'top':0,'z-index':0});
	$('#'+this.holder.img+' img').css({width:this.width,'height':this.height});
	$('#'+this.holder.zoomed).css({'position':'absolute','left':'0px','top':'0px','z-index':1,display:'none'});
	$('#'+this.holder.zoomed+' img').css({width:this.width*this.zoom,'height':this.height*this.zoom});
	$('#'+this.holder.svg).css({'position':'absolute','left':'0px','top':'0px','width':this.width,'height':this.height,'z-index':2});


	this.svg = Raphael(this.holder.svg, this.width, this.height);
	this.scale = this.im.width/this.width;
	this.colours = {calibrator: {text:"rgb(255,255,255)",bg:"rgb(0,255,0)"} };

  this.drawMarkers();

}

Astrometry.prototype.drawMarkers = function(candid) {
  var markers = this.candidates;
  // remove existing markers
  for(var i = 0; i < this.sizer.length ; i++){
    this.sizer[i].remove();
  }
  this.sizer.pop();
  // Draw all the candidate circles
  this.calibrators = this.svg.set();
  this.candidatesszoomed = this.svg.set();
  var sizerid;
  var sizers = new Array();
  for(var i = 0; i < this.candidates.length ; i++){
    // When provided as input the y-axis values are all inverted
    var s = new Sizer(this,markers[i].x/this.scale,(markers[i].y)/this.scale,this.calibrator.r/this.scale,this.calibrator.label+(i+1),$('#'+this.holder.zoomed),{colour:this.colours.calibrator.bg});
    sizers.push(s);
  }
  this.candidatesszoomed.hide();
  this.sizer = sizers;
  var tmparr = this.sizer.reverse();
  this.sizer[this.sizer.length-1].isTwinOf(tmparr.slice(0,-1));

  // Zoom on candidate
  if (candid!=undefined && candid < this.sizer.length){ this.sizer[candid].start();}

}

Astrometry.prototype.changeImage = function(id) {

  var img = document.getElementById('analyser_image');
  var imgz = document.getElementById('analyser_image_zoomed');
  img.src = this.img_stack[id].src;
  imgz.src = this.img_stack[id].src;

  this.candidates = this.img_stack[id].coords;

  this.drawMarkers(zoomcal);
}

Astrometry.prototype.nextImage = function(ind) {
  if (typeof(ind) == 'undefined') {
    index = 0;
  } else {
    index = ind % this.img_stack.length;
  }
  this.changeImage(index);
}

Astrometry.prototype.resetZoom = function(){
  this.zoom = 1;

}

Astrometry.prototype.getView = function(candid){
	this.zoom = this.sizer[0].z

	if(this.zoom==1) return[0,0,1,1];
	else{
		el = $('#'+this.holder.zoomed);
		var p = el.position();
		var fw = el.outerWidth();
		var fh = el.outerHeight();
		var l = (-parseInt(p.left))/fw;
		var t = (-parseInt(p.top))/fh;
		var w = this.width/fw;
		var h = this.height/fh;
		return [l,t,w,h]
	}
}


Astrometry.prototype.getR = function(key){
	var offset = parseInt(key) ? parseInt(key)-1 : 0;
	if(key.indexOf("calibrator")==0){
		offset = (key.length > 10) ? parseInt(key.substr(10))-1 : 0;
		return (this.sizer[offset].r*this.scale);
	}else return 0;
}
Astrometry.prototype.getXs = function(){
	var o = Array();
	for(var i = 0; i < this.sizer.length ; i++){
		o.push(this.sizer[i].x*this.scale);
	}
	return o;
}
Astrometry.prototype.getYs = function(rev){
	var o = Array();
  var tmp_val;
	for(var i = 0; i < this.sizer.length ; i++){
		tmp_val = (!rev) ? (this.im.height-this.sizer[i].y*this.scale) : this.sizer[i].y*this.scale;
    o.push(tmp_val);
	}
	return o;
}
Astrometry.prototype.getRs = function(key){
	var o = "";
	for(var i = 0; i < this.sizer.length ; i++){
		if(i > 0) o += ",";
		o += (this.sizer[i].r*this.scale);
	}
	return o;
}

Astrometry.prototype.addCalibrator = function(x,y,fromfits){
	var i = this.sizer.length;
	if(i < 2) return;	// We should have at least 2 Sizer elements: 1 for sky and 1 for source

	// Need to flip in the y-direction because of the FITS file input
	if(fromfits) y = (this.im.height-y);
	var x = (typeof x=="number") ? x/this.scale : (this.width/2);
	var y = (typeof y=="number") ? y/this.scale : (this.height/2);
	this.sizer[i] = new Sizer(this,x,y,this.sizer[i-1].r,this.calibrator.label+" "+(i-1),$('#'+this.holder.zoomed),{colour:this.colours.calibrator.bg});
	this.sizer[i].cloneEvents(this.sizer[i-1]);
	this.sizer[i].isTwinOf(this.sizer);
	var cal = i-1;
	$('#calibrators').val(cal)
}
Astrometry.prototype.removeCalibrator = function(id){
	if(id < this.sizer.length){
		this.sizer[id].remove()
		this.sizer.pop();

	}
}

Astrometry.prototype.onmove = function(){
  console.log("on move")
	if(this.sizer[0].z > 1){
		p = $('#'+this.holder.zoomed).position();
		this.l = p.left;
		this.t = p.top;

	}
}


Astrometry.prototype.onzoom = function(){
	// Check the zoom level
  console.log("on zoom")
	if(this.sizer[0].z==1){
		// We need to move the zoomed calibrators back
		this.candidatesszoomed.hide();
		this.candidatesszoomed.translate(-this.l,-this.t);
		this.calibrators.show();
	}else{
		p = $('#'+this.holder.zoomed).position();
		this.l = p.left;
		this.t = p.top;
		this.candidatesszoomed.translate(this.l,this.t);
		this.candidatesszoomed.show();
		this.calibrators.hide();

	}
}

Astrometry.prototype.bind = function(e,type,fn){
	if(typeof e!="string" || typeof fn!="function") return this;
	var min = max = 0;

	if(type=="onzoom"){
		var _obj = this;
		var _fn = fn;
		fn = function(args){ _fn.call(this,args); _obj.onzoom(); }
	}
	if(type=="onmove"){
		var _obj = this;
		var _fn = fn;
		fn = function(args){ _fn.call(this,args); _obj.onmove(); }
	}

  if(type=="ondrop"){
		var _obj = this;
		var _fn = fn;
		fn = function(args){ _fn.call(this,args); _obj.ondrop(); }
	}

	for(i = 0; i <= this.sizer.length-1 ; i++) this.sizer[i].bind(type,fn);
	return this;
}
