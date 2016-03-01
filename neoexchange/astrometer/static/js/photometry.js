// Web pages define x,y to start at the top left but FITS is bottom left. The input and output of y will be in FITS definition.
//photo = new Photometry({id:'photometric',src:"{{data.image}}",form:'entryform',width:width,source:{x:s_x,y:s_y,r:start_r},sky:{x:b_x,y:b_y,r:start_r,label:'Sky'},source:{x:c_x[0],y:c_y[0],r:start_r},zoom:2,callback:photoReady,sources:sources});

// To do:
// 1) remove zoom on click.
// 2) make zoom apply to all elements (only one layer)
// 3) when zoomed the user can pan the image (using the rangelimiter?)
// 4) remove ability to resize the radius

function Photometry(inp){

	this.im = new Image();
	this.cur = {x:0,y:0};
	this.width;
	this.height;
	this.zoom = 2;
	this.src;
	this.holder = { id:'imageholder', img: 'imageholder_small', zoomed: 'imageholder_big', svg:'svgcanvas' };
	this.svg;
	this.sources;
	this.sourceszoomed;
	this.source = {x:100,y:0,yfits:500,r:8,label:'Target',callback:''};
	this.sky = {x:100,y:0,yfits:550,r:this.source.r,label:'Sky',callback:''};
	this.source = {x:[100,100,100],y:[0,0,0],yfits:[600,650,700],r:this.source.r,label:'Calibrator',callback:''};
	this.sizer = new Array();
	this.others = new Array();
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
		if(typeof inp.source=="object"){
			if(typeof inp.source.x=="number") this.source.x = inp.source.x;
			if(typeof inp.source.y=="number") this.source.yfits = inp.source.y;
			if(typeof inp.source.r=="number") this.source.r = this.source.r = this.sky.r = inp.source.r;
			if(typeof inp.source.label=="string") this.source.label = inp.source.label;
		}
		if(typeof inp.sky=="object"){
			if(typeof inp.sky.x=="number") this.sky.x = inp.sky.x;
			if(typeof inp.sky.y=="number") this.sky.yfits = inp.sky.y;
			if(typeof inp.sky.r=="number") this.source.r = this.source.r = this.sky.r = inp.sky.r;
			if(typeof inp.sky.label=="string") this.sky.label = inp.sky.label;
		}
		if(typeof inp.source=="object"){
			if(typeof inp.source.x=="object") this.source.x = inp.source.x;
			if(typeof inp.source.y=="object") this.source.yfits = inp.source.y;
			if(typeof inp.source.r=="number") this.source.r = this.source.r = this.sky.r = inp.source.r;
			if(typeof inp.source.label=="string") this.source.label = inp.source.label;
		}
		if(typeof inp.sources=="object") this.others = inp.sources;
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
		if($('#'+this.holder.img).length==0) $('#'+this.holder.id).append('<div id="'+this.holder.img+'"><img src="'+this.src+'" alt="LCOGT image" /></div>');
		if($('#'+this.holder.zoomed).length==0) $('#'+this.holder.id).append('<div id="'+this.holder.zoomed+'" style="display:none;"><img src="'+this.src+'" alt="LCOGT image" /></div>');
		if($('#'+this.holder.svg).length==0) $('#'+this.holder.id).append('<div id="'+this.holder.svg+'"></div>');

		this.pos = $('#'+this.holder.id).position();
	}
}

// We've loaded the image so now we can proceed
Photometry.prototype.loaded = function(){
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
	this.source.y = (this.im.height-this.source.yfits)
	this.source.y = [(this.im.height-this.source.yfits[0]),(this.im.height-this.source.yfits[1]),(this.im.height-this.source.yfits[2])]
	this.sky.y = (this.im.height-this.sky.yfits)
	this.colours = defaultColours();

	// Now draw all the other source circles
	this.sources = this.svg.set();
	this.sourceszoomed = this.svg.set();
	for(var i = 0; i < this.others.length ; i++){
		// When provided as input the y-axis values are all inverted
		o = { x: this.others[i].x/this.scale, y: (this.im.height-this.others[i].y)/this.scale, r : this.others[i].r/this.scale }
		style = {fill: this.colours.source.bg,stroke: "none","stroke-width": 0,opacity: 0.3}
		this.sources.push(this.svg.circle(o.x, o.y, o.r).attr(style));
		this.sourceszoomed.push(this.svg.circle(o.x*this.zoom, o.y*this.zoom, o.r*this.zoom).attr(style));
	}
	this.sourceszoomed.hide()

/*
	// Now draw all the suggested sources
	this.suggestions = this.svg.set();
	this.suggestionszoomed = this.svg.set();
	for(var i = 0; i < this.suggested.length ; i++){
		// When provided as input the y-axis values are all inverted
		s = { x: this.suggested[i].x/this.scale, y: (this.im.height-this.suggested[i].y)/this.scale, r: this.suggested[i].r/this.scale }
		style = {"stroke": this.colours.source.bg,"fill": "none","stroke-width": 2,opacity: 0.5}
		this.suggestions.push(this.svg.circle(s.x, s.y, s.r).attr(style));
		this.suggestions.push(this.svg.reticle(s.x,s.y,s.r*1.4,0.0).attr(style));
		this.suggestionszoomed.push(this.svg.circle(s.x*this.zoom, s.y*this.zoom, s.r*this.zoom).attr(style));
		this.suggestionszoomed.push(this.svg.reticle(s.x*this.zoom, s.y*this.zoom,s.r*1.4*this.zoom,0.0).attr(style));
	}
	if(!this.suggestedvisible){
		this.suggestions.hide();
		this.suggestionszoomed.hide();
	}
	*/

	this.sizer[0] = new Sizer(this,this.sky.x/this.scale,this.sky.y/this.scale,this.sky.r/this.scale,this.sky.label,$('#'+this.holder.zoomed),{colour:this.colours.sky.bg});
	this.sizer[1] = new Sizer(this,this.source.x/this.scale,this.source.y/this.scale,this.source.r/this.scale,this.source.label,$('#'+this.holder.zoomed),{colour:this.colours.source.bg,colourtext:this.colours.source.text});
	this.sizer[2] = new Sizer(this,this.source.x[0]/this.scale,(this.source.y[0])/this.scale,this.source.r/this.scale,this.source.label+' 1',$('#'+this.holder.zoomed),{colour:this.colours.source.bg});
	this.sizer[3] = new Sizer(this,this.source.x[1]/this.scale,(this.source.y[1])/this.scale,this.source.r/this.scale,this.source.label+' 2',$('#'+this.holder.zoomed),{colour:this.colours.source.bg});
	this.sizer[4] = new Sizer(this,this.source.x[2]/this.scale,(this.source.y[2])/this.scale,this.source.r/this.scale,this.source.label+' 3',$('#'+this.holder.zoomed),{colour:this.colours.source.bg});
	this.sizer[4].isTwinOf([this.sizer[0],this.sizer[1],this.sizer[2],this.sizer[3]]);

}
Photometry.prototype.getView = function(){
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

Photometry.prototype.getX = function(key){
	var offset = parseInt(key) ? parseInt(key)-1 : 0;
	if(key == "sky")  return (this.sizer[0].x*this.scale);
	else if(key == "source") return (this.sizer[1].x*this.scale);
	else if(key.indexOf("source")==0){
		offset = (key.length > 10) ? parseInt(key.substr(10))-1 : 0;
		return (this.sizer[2+offset].x*this.scale);
	}else return 0;
}
Photometry.prototype.getY = function(key,rev){
	var y = 0;
	if(key == "sky")  y = this.sizer[0].y;
	else if(key == "source") y = this.sizer[1].y;
	else if(key.indexOf("source")==0){
		offset = (key.length > 10) ? parseInt(key.substr(10))-1 : 0;
		y = this.sizer[2+offset].y;
	}
	if(!rev) return this.im.height-y*this.scale;
	else return y*this.scale;
}
Photometry.prototype.getR = function(key){
	var offset = parseInt(key) ? parseInt(key)-1 : 0;
	if(key == "sky")  return (this.sizer[0].r*this.scale);
	else if(key == "source") return (this.sizer[1].r*this.scale);
	else if(key.indexOf("source")==0){
		offset = (key.length > 10) ? parseInt(key.substr(10))-1 : 0;
		return (this.sizer[2+offset].r*this.scale);
	}else return 0;
}
Photometry.prototype.getXs = function(){
	var o = "";
	for(var i = 0; i < this.sizer.length ; i++){
		if(i > 0) o += ",";
		o += (this.sizer[i].x*this.scale);
	}
	return o;
}
Photometry.prototype.getYs = function(rev){
	var o = "";
	for(var i = 0; i < this.sizer.length ; i++){
		if(i > 0) o += ",";
		o += (!rev) ? (this.im.height-this.sizer[i].y*this.scale) : this.sizer[i].y*this.scale;
	}
	return o;
}
Photometry.prototype.getRs = function(key){
	var o = "";
	for(var i = 0; i < this.sizer.length ; i++){
		if(i > 0) o += ",";
		o += (this.sizer[i].r*this.scale);
	}
	return o;
}

Photometry.prototype.gaussian = function(inp,x,y){
	// Scale = inp[0]
	// Sigma = inp[1]
	// x = p[2]
	// y = p[3]
	// bg = p[4:]
	var sig2 = inp[1]*inp[1];
	var dx = (x+inp[2]);
	var dy = (y+inp[3]);
	var diff = Math.sqrt(dx*dx + dy*dy);
	var r = inp[0] * Math.exp(-0.5 * diff * diff / sig2);
	//if(diff*diff < sig2) r = 255;
	for (j = 4; j < inp.length; j++) r += inp[j] * Math.pow(dx, j-4);

	if(r > 255) r = 255;
	return r;
}

Photometry.prototype.flatgaussian = function(inp,x,y){
	// Scale = inp[0]
	// Sigma = inp[1]
	// x = inp[2]
	// y = inp[3]
	// xflat = inp[4];
	// bg = inp[5:]
	var sig2 = inp[1]*inp[1];
	var dx = (x+inp[2]);
	var dy = (y+inp[3]);
	var diff = Math.sqrt(dx*dx + dy*dy);
	var r = inp[5] + inp[0] * Math.exp(-0.5 * diff * diff / sig2);
	if(diff < inp[4] && r > 255) r = 255.0;
	return r;
}

Photometry.prototype.makeThumbnail = function(width,height,id){

	id = (!id) ? 'thumbnail' : id;
	if(this.ctx && this.ctx[id]) return;

	$('#toolbar').append('<div id="'+id+'"></div>');

	// Now we want to build the <canvas> element that will hold our image
	var el = document.getElementById(id);
	if(el!=null){
		// Look for a <canvas> with the specified ID or fall back on a <div>
		if(typeof el=="object" && el.tagName != "CANVAS"){
			// Looks like the element is a container for our <canvas>
			el.setAttribute('id',id+'holder');
			var canvas = document.createElement('canvas');
			canvas.style.display='block';
			canvas.setAttribute('width',width);
			canvas.setAttribute('height',height);
			canvas.setAttribute('id',id);
			el.appendChild(canvas);
			// For excanvas we need to initialise the newly created <canvas>
			if(/*@cc_on!@*/false) el = G_vmlCanvasManager.initElement(this.canvas);
		}else{
			// Define the size of the canvas
			// Excanvas doesn't seem to attach itself to the existing
			// <canvas> so we make a new one and replace it.
			if(/*@cc_on!@*/false){
				var canvas = document.createElement('canvas');
				canvas.style.display='block';
				canvas.setAttribute('width',width);
				canvas.setAttribute('height',height);
				canvas.setAttribute('id',id);
				el.parentNode.replaceChild(canvas,el);
				if(/*@cc_on!@*/false) el = G_vmlCanvasManager.initElement(elcanvas);
			}else{
				el.setAttribute('width',width);
				el.setAttribute('height',height);
			}
		}
		this.canvas = document.getElementById(id);
	}else this.canvas = el;
	if(!this.ctx) this.ctx = {};
	this.ctx[id] = (this.canvas) ? this.canvas.getContext("2d") : null;

}
Photometry.prototype.peakShift = function(ox,oy,counter,iter){

	var showThumb = false;
	var w = 23;
	var h = 23;
	var i = j = x = n = y = s = p = v = dx = dy = offx = offy = mx = 0;
	var id = 'thumbnail'+counter
	var diff;
	var threshold = 235;
	var cutout = [];
	for(i = 0; i < w ; i++){
		cutout.push([]);
		for(j = 0; j < h ; j++){
			cutout[i].push(0);
		}
	}

	if(showThumb){
		this.makeThumbnail(w,h,id);
		var thumbData = this.ctx[id].createImageData(w,h);
	}

	var tx,ty;
	if(!iter || iter > 8) iter = 8;

	// Do we need to scale the threshold
	for(y = -h/2, j = 0; y < h/2; y++, j++){
		for(x = -w/2, i = 0; x < w/2; x++, i++){
			tx = x+dx;
			ty = y+dy;
			if((ox+tx) < 0 || (ox+tx > this.imageData.width) || (oy+ty) < 0 || (oy+ty > this.imageData.height)) continue;
			p = ((this.imageData.height-Math.round(oy-ty))*this.imageData.width+Math.round(ox+tx))*4;
			v = (this.imageData.data[p]+this.imageData.data[p+1]+this.imageData.data[p+2])/3;

			diff = (tx*tx + ty*ty);
			if(diff < w/2 && v > threshold) n++;
		}
	}
	if(n < 10) threshold *= 0.8;

	n = 0;

	// Try to optimize the position
	for(var loop = 0 ; loop < iter ; loop++){
		for(y = -h/2, j = 0; y < h/2; y++, j++){
			for(x = -w/2, i = 0; x < w/2; x++, i++){
				tx = x+dx;
				ty = y+dy;
				if((ox+tx) < 0 || (ox+tx > this.imageData.width) || (oy+ty) < 0 || (oy+ty > this.imageData.height)) continue;
				p = ((this.imageData.height-Math.round(oy-ty))*this.imageData.width+Math.round(ox+tx))*4;
				v = (this.imageData.data[p]+this.imageData.data[p+1]+this.imageData.data[p+2])/3;

				diff = (tx*tx + ty*ty);
				if(diff < 1) diff = 1;
				v = (v > threshold) ? 255 : 0;
				if(Math.sqrt(diff) > w/2) v /= 3;	// Only OK within circle
				cutout[x+w/2][y+h/2] = v;

			}
		}

		// Fill in holes
		for(i = 0; i < w ; i++){
			for(j = 0; j < h ; j++){
				if(cutout[i][j]==0){

					if(i>w/3 && i < w*2/3 && cutout[i-1][j] == 255 && cutout[i+1][j] == 255) cutout[i][j] = 255;
					if(j>w/3 && j < h*2/3 && cutout[i][j-1] == 255 && cutout[i][j+1] == 255) cutout[i][j] = 255;
				}
			}
		}

		if(showThumb){
			// Make the thumbnail
			for(i = 0; i < w ; i++){
				for(j = 0; j < h ; j++){
					p = (w*(j) + (i))*4;
					thumbData.data[p] = cutout[i][j];
					thumbData.data[p+1] = cutout[i][j];
					thumbData.data[p+2] = cutout[i][j];
					thumbData.data[p+3] = 255;
				}
			}
			this.ctx[id].putImageData(thumbData, 0, 0);
		}

		// Work out the centre of mass in the x and y directions
		n = 0;
		x = 0;
		y = 0;
		for(i = 0; i < w ; i++){
			for(j = 0; j < h ; j++){
				if(cutout[i][j] > 0){
					s = (cutout[i][j]/255);
					x += (1+i)*s;
					y += (1+j)*s;
					n += 1*s;
				}
			}
		}
		offx = (n > 10 && n < (w*h)/3) ? (x/n)-w/2 : 0;
		offy = (n > 10 && n < (w*h)/3) ? (y/n)-h/2 : 0;
		if(Math.abs(offx) < 0.3 && Math.abs(offy) < 0.3) iter = loop;
		dx += offx;
		dy += offy;

	}

	return [0,0,dx,dy];

}
Photometry.prototype.fineTune = function(){

	var canvas = document.createElement("canvas");
	canvas.width = this.im.width;
	canvas.height = this.im.height;
	var ctx = canvas.getContext("2d");
	ctx.drawImage(this.im,0,0,this.im.width,this.im.height);
	if(!this.imageData) this.imageData = ctx.getImageData(0,0,this.im.width,this.im.height);

	var ox,oy,z,dx,dy,d;

	z = this.sizer[0].zoomLevel();

	ox = this.getX("source");
	oy = this.getY("source");
	d = this.peakShift(ox,oy,'a');
	this.sizer[1].moveNoZoom(d[2],d[3]);

	for(var c = 2; c < this.sizer.length; c++){
		ox = this.getX("source"+(c-1));
		oy = this.getY("source"+(c-1));
		d = this.peakShift(ox,oy,c-1);
		this.sizer[c].moveNoZoom(d[2],d[3]);
	}

}
Photometry.prototype.addCalibrator = function(x,y,fromfits){
	var i = this.sizer.length;
	if(i < 2) return;	// We should have at least 2 Sizer elements: 1 for sky and 1 for source

	// Need to flip in the y-direction because of the FITS file input
	if(fromfits) y = (this.im.height-y);
	var x = (typeof x=="number") ? x/this.scale : (this.width/2);
	var y = (typeof y=="number") ? y/this.scale : (this.height/2);
	this.sizer[i] = new Sizer(this,x,y,this.sizer[i-1].r,this.source.label+" "+(i-1),$('#'+this.holder.zoomed),{colour:this.colours.source.bg});
	this.sizer[i].cloneEvents(this.sizer[i-1]);
	this.sizer[i].isTwinOf(this.sizer);
	var cal = i-1;
	// Do the form fields already exist? If they do, don't add them again!
	if($('#id_cal'+cal+'radius').length == 0){
		var html = '<div class="fieldWrapper"><label for="id_cal'+cal+'radius">Aperture Radius (source '+cal+')</label><input type="text" name="cal'+cal+'radius" id="id_cal'+cal+'radius" /></div>';
		html += '<div class="fieldWrapper"><label for="id_cal'+cal+'xpos">Calibrator '+cal+' x position</label><input type="text" name="cal'+cal+'xpos" id="id_cal'+cal+'xpos" /></div>';
		html += '<div class="fieldWrapper"><label for="id_cal'+cal+'ypos">Calibrator '+cal+' y position</label><input type="text" name="cal'+cal+'ypos" id="id_cal'+cal+'ypos" /></div>';
		html += '<div class="fieldWrapper"><label for="id_cal'+cal+'counts">Calibrator '+cal+' counts</label><input type="text" name="cal'+cal+'counts" id="id_cal'+cal+'counts" /></div>';
		$('#'+this.form).append(html);
	}
	$('#sources').val(cal)
}
Photometry.prototype.removeCalibrator = function(x,y){
	if(this.sizer.length > 5){
		this.sizer[this.sizer.length-1].remove()
		this.sizer.pop();
		var n = $('#'+this.form+' .fieldWrapper').length;
		$('#'+this.form+' .fieldWrapper:gt('+(n-5)+')').remove()
	}
}
/*
Photometry.prototype.toggleSuggestions = function(){
	this.suggestedvisible = !this.suggestedvisible;
	if(this.suggestedvisible) this.suggestions.show();
	else this.suggestions.hide();
	this.suggestionszoomed.hide();
}*/
Photometry.prototype.onmove = function(){

	if(this.sizer[0].z > 1){
		p = $('#'+this.holder.zoomed).position();
		this.l = p.left;
		this.t = p.top;
//		this.sourceszoomed.translate(10,10);
//		console.log('onmove',this.sourceszoomed)
	}
}
Photometry.prototype.onzoom = function(){
	// Check the zoom level

	if(this.sizer[0].z==1){
		// We need to move the zoomed sources back
		this.sourceszoomed.hide();
		this.sourceszoomed.translate(-this.l,-this.t);
		this.sources.show();
/*
		this.suggestionszoomed.translate(-this.l,-this.t)
		if(this.suggestedvisible){
			this.suggestionszoomed.hide();
			this.suggestions.show();
		}else{
			this.suggestionszoomed.hide();
			this.suggestions.hide();
		}
		*/
	}else{
		p = $('#'+this.holder.zoomed).position();
		this.l = p.left;
		this.t = p.top;
		this.sourceszoomed.translate(this.l,this.t);
		this.sourceszoomed.show();
		this.sources.hide();
		/*
		this.suggestionszoomed.translate(this.l,this.t)
		if(this.suggestedvisible){
			this.suggestionszoomed.show();
			this.suggestions.hide();
		}else{
			this.suggestionszoomed.hide();
			this.suggestions.hide();
		}*/
	}
}
Photometry.prototype.bind = function(e,type,fn){
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

	if(e == "sky"){ min = 0; max = 0; }
	else if(e == "source"){ min = 1; max = 1; }
	else if(e == "source"){ min = 2; max = this.sizer.length-1; }

	for(i = min; i <= max ; i++) this.sizer[i].bind(type,fn);
	return this;
}
