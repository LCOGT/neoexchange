function Sizer(canvas,x,y,r,label,zoomed,config) {
	if(typeof config!="object") config = {};
	this.canvas = canvas;
	this.me = canvas.svg;
	this.zoom = zoomed || "";
	this.pos = {x:((typeof x=="number") ? x : 100),y:((typeof y=="number") ? y : 100),r:((typeof r=="number") ? r : 10)};
	this.d2r = (Math.PI/180);
	this.x = (typeof x=="undefined") ? 100 : x;
	this.y = (typeof y=="undefined") ? 100 : y;
	this.r = (typeof r=="undefined") ? 10 : r;
	this.l;
	this.t;
	this.z = 1;
	this.ox = this.x;
	this.oy = this.y;
	this.maxr = 70;
	this.master;
	this.visible = true;
	this.twins = [];
	this.caption = label || "";
	this.moving = false;
	this.sizing = false;
	this.colour = (typeof config.colour=="string") ? config.colour : 'rgb(255,255,255)';
	this.colourtext = (typeof config.colourtext=="string") ? config.colourtext : 'rgb(0,0,0)';
	this.events = { onzoom:"", onclick: "", ondrop:"", onmove: "" };
	this.fontsize = 12;
	this.angle = this.goodAngle(-30);

	this.s = this.me.circle(this.x, this.y, this.r).attr({
		fill: "none",
		stroke: this.colour,
		"stroke-width": 2,
		opacity: 1
	});
	this.reticle = this.me.reticle(this.x,this.y,this.r,-this.angle).attr({
		fill: "none",
		stroke: this.colour,
		"stroke-width": 1,
		opacity: 0
	});
	this.me.txtattr = {'font-size':this.fontsize};

	this.dx = Math.cos(this.angle*this.d2r);
	this.dy = -Math.sin(this.angle*this.d2r);
	this.label = this.me.handle(this.x+this.pos.r*this.dx,this.y+this.pos.r*this.dy,this.caption,this.angle).attr([{fill: this.colour,stroke: "none",cursor:'pointer'},{fill:this.colourtext,cursor:'pointer'}]);
	this.label.drag(this.move,this.start,this.up,this);
}
Sizer.prototype.goodAngle = function(a){
	if(typeof a=="undefined") a = 350;
	else a = (a+360)%360;
	var wide = (this.caption.length*10);	// A rough guess of the length
	var l = (this.x < this.r+wide);
	var r = (this.x > this.me.width-this.r-wide);
	var b = (this.y > this.me.height-this.r-wide);
	var t = (this.y < this.r+wide);
	if(r && (a > 270 || a < 90)) a = 180-a;
	if(l && (a > 90 && a < 270)) a = 180-a;
	if((b && (a > 180 || a < 0)) || (t && (a < 180 && a > 0))) a = (360-a);
	return (a+360)%360;
}
Sizer.prototype.hide = function(){
	this.visible = false;
	this.s.attr('opacity',0);
	this.label.attr('opacity',0);
}
Sizer.prototype.show = function(){
	this.visible = true;
	this.s.attr('opacity',1);
	this.label.attr('opacity',1);
}
Sizer.prototype.remove = function(){
	this.s.remove();
	this.label.remove();
	this.reticle.remove();
}
Sizer.prototype.positionLabel = function(x,y,t,a){
	if(typeof x=="undefined") var x = this.pos.x;
	else{
		if(typeof y=="undefined"){
			var a = x;
			var x = this.pos.x;
			var y = this.pos.y;
			var t = this.label.caption;
		}
	}
	if(typeof y=="undefined") var y = this.pos.y;
	if(typeof t=="undefined") var t = this.label.caption;
	if(typeof a=="undefined") var a = this.angle;
	else{
		this.angle = a;
		this.dx = Math.cos(a*this.d2r);
		this.dy = -Math.sin(a*this.d2r);
	}
	this.label.update((x+this.r*this.dx),(y+this.r*this.dy),t,a);
}
Sizer.prototype.appendLabel = function(txt){
	this.positionLabel();
	if(!this.visible) this.label.attr({'opacity':0});
}
Sizer.prototype.isTwinOf = function(szs){
	if(typeof szs.length=="undefined") szs = [szs];

	for(var sz = 0; sz < szs.length ; sz++){
		found = 0;
		for(var i = 0; i < this.twins ; i++){
			if(this.twins[i] == szs[sz]) found = 1;
		}
		// Store my twin if it wasn't already known about
		if(!found && szs[sz]!=this) this.twins.push(szs[sz]);
	}
	
	// Loop over my twins and reset all their twins
	for(var i = 0; i < this.twins.length ; i++){
		this.twins[i].twins = [];
		// Make me a twin of my twin
		this.twins[i].twins.push(this);
		for(var j = 0; j < this.twins.length ; j++){
			if(this.twins[j] != this.twins[i]) this.twins[i].twins.push(this.twins[j]);
		}
	}
}
Sizer.prototype.removeTwin = function(sz){
	// Easiest thing is to work out new twin list, zap all the twins of twins, remove current twins and set new twin list
	var temptwins = [];
	for(var i = 0; i < this.twins ; i++){
		if(this.twins[i] != sz) temptwins[j++] = this.twins[i];
		this.twins[i].twins = [];
	}
	this.isTwinOf(temptwins);
}
Sizer.prototype.getX = function(){ return (this.pos.x-this.pos.x*this.z); }
Sizer.prototype.getY = function(){ return (this.pos.y-this.pos.y*this.z); }
Sizer.prototype.shiftMe = function(lin,tin){
	this.l = lin;
	this.t = tin;
	x = ((typeof this.zoom=="object" && this.z != 1) ? this.l : 0)+this.pos.x*this.z;
	y = ((typeof this.zoom=="object" && this.z != 1) ? this.t : 0)+this.pos.y*this.z;
	this.reticle.attr({opacity:0});
	r = this.pos.r*this.z;
	this.r = this.pos.r*this.z;

	this.s.attr({cx: x, cy: y, r: r});
	this.positionLabel(x, y);
};
Sizer.prototype.redraw = function(){

	this.r = this.pos.r*this.z;
	this.positionLabel(this.x, this.y);
	if(this.moving){
		this.reticle.update(this.x,this.y,this.r)
		this.s.attr({cx: this.x, cy: this.y});
	}else{
		this.s.attr({cx: this.x, cy: this.y, r: this.r});
	}
}
Sizer.prototype.updateZoom = function(z){
	this.z = z || 1;
	if(typeof this.twins == "object"){
		for(var i=0; i<this.twins.length ;i++){
			this.twins[i].l = this.l;
			this.twins[i].t = this.t;
			this.twins[i].z = this.z;
			this.twins[i].shiftMe(this.l,this.t);
		}
	}
	this.s.attr({r: this.pos.r*this.z});
	this.triggerEvent("onzoom");
}
Sizer.prototype.zoomLevel = function(){
	return this.zoom.width()/this.me.width;
}
Sizer.prototype.start = function(){
	if(!this.visible) return;
	this.moving = true;
	this.label.attr([{cursor:'grabbing',cursor:'-moz-grabbing'},{cursor:'grabbing',cursor:'-moz-grabbing'}]);
	this.reticle.attr({opacity: 1});
	this.appendLabel('');	// Reset any text appended to the label
	if(typeof this.zoom=="object"){
		this.z = this.zoomLevel();
		this.l = this.getX();
		this.t = this.getY();
		this.zoom.css({'display':'inline',left:this.l,top:this.t})
	}
	if(typeof this.zoom=="object") this.updateZoom(this.zoomLevel());
	this.redraw();
	if(this.canvas.groupmove || this.canvas.shiftkey){
		if(typeof this.twins == "object"){
			for(var i=0; i<this.twins.length ;i++){
				this.twins[i].l = this.l;
				this.twins[i].t = this.t;
				this.twins[i].z = this.z;
				this.twins[i].shiftMe(this.l,this.t);
			}
		}
	}
	this.triggerEvent("onclick");
	this.triggerEvent("onmove",{x:((this.x-this.l)/this.z)/this.me.width,y:((this.y-this.t)/this.z)/this.me.height})
}
Sizer.prototype.move = function(dx,dy){
	if(!this.visible) return;
	// Calculate new position
	this.x = this.pos.x + dx;
	this.y = this.pos.y + dy;
	// Check for out-of-range issue for x,y coordinates
	if(this.x < 0) this.x = 0;
	if(this.y < 0) this.y = 0;
	if(this.x > this.me.width) this.x = this.me.width;
	if(this.y > this.me.height) this.y = this.me.height;
	this.redraw();


	if(this.canvas.groupmove || this.canvas.shiftkey){
		if(typeof this.twins == "object"){
			for(var i=0; i<this.twins.length ;i++){
				this.twins[i].l = this.l;
				this.twins[i].t = this.t;
				this.twins[i].z = this.z;
				this.twins[i].shiftMe(this.l+dx,this.t+dy);
			}
		}
	}

	this.triggerEvent("onmove",{x:((this.x-this.l)/this.z)/this.me.width,y:((this.y-this.t)/this.z)/this.me.height});
}
Sizer.prototype.moveNoZoom = function(dx,dy){
	var z = this.zoomLevel();
	this.move(dx/z,dy/z);
	this.pos.x = this.x;
	this.pos.y = this.y;
	this.redraw();
}
Sizer.prototype.up = function() {
	if(!this.visible) return;
	this.pos.x = (this.x-this.l)/this.z;
	this.pos.y = (this.y-this.t)/this.z;
	this.moving = false;
	var dx = this.x-this.pos.x;
	var dy = this.y-this.pos.y;
	this.x = this.pos.x;
	this.y = this.pos.y;

	if(this.canvas.groupmove || this.canvas.shiftkey){
		if(typeof this.twins == "object"){
			for(var i=0; i<this.twins.length ;i++){
				this.twins[i].x += dx;
				this.twins[i].y += dy;
				this.twins[i].pos.x += dx;
				this.twins[i].pos.y += dy;
				// Check for out-of-range issue for x,y coordinates
				if(this.twins[i].x < 0) this.twins[i].x = 0;
				if(this.twins[i].y < 0) this.twins[i].y = 0;
				if(this.twins[i].x > this.me.width) this.twins[i].x = this.me.width;
				if(this.twins[i].y > this.me.height) this.twins[i].y = this.me.height;
				this.twins[i].redraw();
			}
		}
	}

	// restoring state
	if(typeof this.zoom=="object") this.updateZoom(1);
	if(typeof this.zoom=="object") this.zoom.css({'display':'none'});
	this.reticle.attr({opacity: 0});
	this.positionLabel(this.goodAngle(this.angle));
	this.label.attr([{cursor:'pointer'},{cursor:'pointer'}]);


	this.redraw();
	this.triggerEvent("ondrop");
}
Sizer.prototype.changeRadius = function(){
	this.updateRadius(Math.sqrt(Math.pow(this.canvas.cur.x-this.ox,2) + Math.pow(this.canvas.cur.y-this.oy,2)));
	if(typeof this.twins == "object"){
		for(var i=0; i<this.twins.length ;i++) this.twins[i].updateRadius(this.r*this.z);
	}
}
Sizer.prototype.updateRadius = function(newr){
	if(newr < 1) newr = 1;
	if(newr > this.maxr) newr = this.maxr;
	this.s.attr({r: newr});
	this.r = newr/this.z;
	this.positionLabel();
}
Sizer.prototype.bind = function(ev,fn){
	if(typeof ev!="string" || typeof fn!="function") return this;
	if(this.events[ev]) this.events[ev].push(fn);
	else this.events[ev] = [fn];
	return this;
}
Sizer.prototype.triggerEvent = function(ev,args){
	if(typeof ev != "string") return;
	if(typeof args != "object") args = {};
	var o = [];
	var _obj = this;
	if(typeof this.events[ev]=="object"){
		for(i = 0 ; i < this.events[ev].length ; i++){
			if(typeof this.events[ev][i] == "function") o.push(this.events[ev][i].call(_obj,args))
		}
	}
	if(o.length > 0) return o
}
Sizer.prototype.cloneEvents = function(s){
	this.events = s.events;
}
Raphael.fn.reticle = function (cx, cy, r, angle) {
	this.r = r || 10;
	this.f = (this.r > 10) ? this.r-5 : this.r*0.8;
	this.cx = cx;
	this.cy = cy;
	this.a = angle || 0;
	var res = this.set();
	res.push(this.path().attr({"fill":"black","stroke":this.colour}));
	res.update = function(cx,cy,r,a){
		this.cx = cx;
		this.cy = cy;
		this.r = r;
		this.a = a;
		var f = (r > 10) ? r-5 : r*0.8;
		var points = ["M", cx, cy, "m", -r, 0, "l", f, 0, "M", cx, cy,"m",r,0,"l",-f,0,"M",cx,cy,"m",0,-r,"l",0,f,"M",cx,cy,"m",0,r,"l",0,-f];
		this.attr({path: points.join()}).rotate(a,0,0);
		return this;
	}
	return res.update(cx, cy, this.r, this.a);
}
Raphael.fn.handle = function (x, y, text, angle) {
	var angle = angle || 0;
	var text = text || "blank";
	var res = this.set();
	res.push(this.path().attr({fill: "#000", stroke: "none"}));
	res.push(this.text(x, y, text).attr(this.txtattr).attr({fill: "#fff",'text-anchor':'middle'}));
	res.update = function (x, y, t, a) {
		if(typeof t=="string") text = t;
		if(typeof a=="number") angle = a;
		this.rotate(0, x, y);
		var bb = this[1].getBBox(),
		h = bb.height / 2,
		d = 3;
		this[0].attr({path: ["M", x, y, "l", h + d, -h - d, bb.width + 2 * d, 0, 0, bb.height + 2 * d, -bb.width - 2 * d, 0, "z"].join(",")});
		this[1].attr({x: x + h + d + bb.width/2, y: y});
		angle = 360 - angle;
		this.rotate(angle, x, y);
		angle > 90 && angle < 270 && this[1].attr({x: x - h - d - bb.width/2, y: y,rotation: [180 + angle, x, y]});
		return this;
	};
	return res.update(x, y, text, angle);
};
