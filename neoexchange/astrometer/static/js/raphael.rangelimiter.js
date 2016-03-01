// Create a range limiting rectangles.
// e.g. 
// 		limit = new RangeLimiter({id:'finderthumb','stroke':'#ff0000',opacity:0.3,'strokewidth':1.5,limits:[{x:20,y:40,w:20,h:60,opacity:0.1,stroke:'#66ff99'},{x:100,y:80,w:20,h:20,opacity:0.3,stroke:'#bb9922'},{x:100,y:140,w:70,h:20,opacity:0.2,stroke:'#bb22bb'}]})
//
// Options
// =======
// id = The id of the element to attach this to. It should contain an <img>
// stroke = The default line colour
// strokewidth = The default line width
// opacity = The default opacity of the filled rectangle
// limits = An array of structures each containing {x, y, w, h, opacity, stroke, strokewidth}
//
// Functions
// =========
// limit.addRegion(inp)
// 	- Create a new sizable rectangle. The input object should contain x, y, width and height.
// 	  Optional arguments are 'stroke' (colour), 'strokewidth', and 'opacity'.
// limit.getCoords(i)
// 	- Get the normalised (0-1) coordinates for the ith rectangle. These will be in the order xmin, ymin, xmax, ymax.


// This function requires an element to be attached to. 
function RangeLimiter(id,inp) {

	this.limits = new Array();
	this.ready = false;
	this.visible = true;
	this.r = new Array();
	this.ishole = false;

	// el should be the string that can be used in $(x) to get a holder
	if(typeof id=="string"){
		// If we don't find it, or there are more than one, we bail out
		if($('#'+id).length != 1) return false;
		// If we get here, it looks as though things are OK so set the holder
		this.id = id;
	}
	if(typeof id=="object" && typeof inp=="undefined"){
		// We'll allow the user to provide a single structure with all the config options
		inp = id;
		if(typeof inp.id=="string") this.id = inp.id;
		else return false;
	}else return false;

	// Overwrite defaults with variables passed to the function
	if(typeof inp=="object"){
		this.stroke = (typeof inp.stroke=="string") ? inp.stroke : '#ff0000';
		this.strokewidth = (typeof inp.strokewidth=="number") ? inp.strokewidth : 1;
		if(typeof inp.limits=="object") this.limits = inp.limits;
		if(typeof inp.imageclick=="function") this.imageclick = inp.imageclick;
		this.opacity = (typeof inp.opacity=="number") ? inp.opacity : 0.1;
	}

	if($('#'+this.id+' img').length < 1) return false;
	this.holder = this.id+'_holder';

	this.src = $('#'+this.id+' img').attr('src');
	if(this.src){
		this.ready = true;
		this.width = $('#'+this.id+' img').innerWidth();
		this.height = $('#'+this.id+' img').innerHeight();
		// Zap existing content
		$('#'+this.id).prepend('<div id="'+this.holder+'" style="float:left;position:absolute;"></div>');
		this.x = $('#'+this.id).offset().left;
		this.y = $('#'+this.id).offset().top;
		this.svg = Raphael(this.holder, this.width, this.height);
		//this.img = this.svg.image(this.src,0,0,this.width,this.height)
		if(typeof this.imageclick=="function") $('#'+this.holder).bind('click',this.imageclick)
		for(var i = 0 ; i < this.limits.length ; i++) this.addRegion(this.limits[i]);
	}
	return this;
}

// All coordinates should be normalised from 0-1
RangeLimiter.prototype.addRegion = function(inp){
	if(!this.ready) return false;
	if(typeof this.r=="undefined") this.r = new Array(1);
	this.r[this.r.length] = new ResizableRectangle(this,inp.x,inp.y,inp.w,inp.h,inp)
}

RangeLimiter.prototype.getCoords = function(i){
	if(i < 0 || i >= this.r.length) return false;
	var r = this.r[i];
	return [(r.xmin/r.canvas.width),(r.ymin/r.canvas.height),(r.xmin+r.width)/r.canvas.width,(r.ymin+r.height)/r.canvas.height]
}

RangeLimiter.prototype.resize = function(inp,i){
	if(typeof i!="number") i = 0;
	if(i < this.r.length){
		if(typeof inp=="object" && inp.length!=4) inp = [0,0,1,1];
		this.r[i].resize(inp[0],inp[1],inp[2],inp[3]);
	}
}

RangeLimiter.prototype.show = function(i){
	this.visible = true;
	if(typeof i=="number") this.r[i].show();
	else{
		for(i = 0; i < this.r.length ; i++) this.r[i].show();
	}
}
RangeLimiter.prototype.hide = function(i){
	this.visible = false;
	if(typeof i=="number") this.r[i].hide();
	else{
		for(i = 0; i < this.r.length ; i++) this.r[i].hide();
	}
}

function ResizableRectangle(canvas,x,y,width,height,inp) {

	this.canvas = canvas;
	this.svg = canvas.svg;

	this.stroke = this.canvas.stroke;
	this.strokewidth = this.canvas.strokewidth;
	this.opacity = this.canvas.opacity;
	this.visible = true;
	this.ishole = false;
	this.xonly = false;
	this.yonly = false;

	if(typeof inp=="object"){
		if(typeof inp.stroke=="string") this.stroke = inp.stroke;
		if(typeof inp.strokewidth=="number") this.strokewidth = inp.strokewidth;
		if(typeof inp.opacity=="number") this.opacity = inp.opacity;
		if(typeof inp.visible=="boolean") this.visible = inp.visible;
		if(typeof inp.hole=="boolean") this.ishole = inp.hole;
		if(typeof inp.xonly=="boolean") this.xonly = inp.xonly;
		if(typeof inp.yonly=="boolean") this.yonly = inp.yonly;
	}

	// Scale the 0-1 input values to the actual canvas size
	x *= this.canvas.width;
	y *= this.canvas.height;
	width *= this.canvas.width;
	height *= this.canvas.height;

	this.width = width;
	this.height = height;
	this.xmin = x;
	this.xmax = x+width;
	this.ymin = y;
	this.ymax = y+height;
	this.moving = false;
	this.xcur = width/3;
	this.ycur = width/4;
	if(this.ishole){
		this.hole = this.svg.path(this.recthole(this.xmin,this.ymin,this.width,this.height)).attr({
			fill:this.stroke,
			stroke: "none",
			opacity: 0.5
		});
	}
	this.r = this.svg.rect(this.xmin,this.ymin,this.width,this.height);
	this.r.attr({
		fill:this.stroke,
		stroke: "none",
		opacity: this.opacity
	})
	this.b = this.svg.rect(this.xmin,this.ymin,this.width,this.height).attr({'stroke':this.stroke,'stroke-width':this.strokewidth});
	this.crosshair = this.svg.crosshair(this,this.xcur,this.ycur).attr({ stroke: this.stroke,'stroke-width':this.strokewidth });
	this.r.drag(this.move,this.start,this.up,this);
	this.b.drag(this.bmove,this.bstart,this.bup,this);
	this.b.mousemove(function (e) {
		this.setDir(e);
		if(this.dir) this.b.attr({cursor:this.dir+'-resize','stroke-width':this.strokewidth*1.5});
		else this.b.attr({cursor:'normal','stroke-width':this.strokewidth});
	},this).mouseout(function (e) {
		if(!this.moving && !this.sizing) this.b.attr({'stroke-width':this.strokewidth});
	},this);
	this.r.mousemove(function (e) {
		this.b.attr({'stroke-width':this.strokewidth*1.5});
	},this).mouseout(function (e) {
		this.b.attr({'stroke-width':this.strokewidth});
	},this);
	if(!this.visible) this.hide();
}

ResizableRectangle.prototype.hide = function(){
	this.visible = false;
	this.r.hide();
	this.b.hide();
	this.crosshair.hide();
}

ResizableRectangle.prototype.show = function(){
	this.visible = true;
	this.r.show();
	this.b.show();
	this.crosshair.show();
}

ResizableRectangle.prototype.resize = function(x,y,w,h,cx,cy){
	this.r.attr({x:x*this.canvas.width,y:y*this.canvas.height,width:w*this.canvas.width,height:h*this.canvas.height});
	this.b.attr({x:x*this.canvas.width,y:y*this.canvas.height,width:w*this.canvas.width,height:h*this.canvas.height});
	if(cx && cy) this.crosshair.update(this,x*this.canvas.width,y*this.canvas.height);
}

ResizableRectangle.prototype.setDir = function(e){
	//if(!this.yonly && (this.dir.indexOf('e') > 0 || this.dir.indexOf('w') > 0)) 
	if(!this.sizing){
		this.dir = "";
		dx = (e.pageX-this.canvas.x-this.xmin-this.width/2)
		dy = (e.pageY-this.canvas.y-this.ymin-this.height/2)
		if(dx >= this.width/2 - 2 && !this.yonly) this.dir = 'e'
		if(dx <= -this.width/2 + 2 && !this.yonly) this.dir = 'w'
		if(dy <= -this.height/2 + 2 && !this.xonly) this.dir = 'n'
		if(dy >= this.height/2 - 2 && !this.xonly) this.dir = 's'
		if(dx >= this.width/2 - 2 && dy >= this.height/2 - 2 && !this.yonly && !this.xonly) this.dir = 'se'
		if(dx <= -this.width/2 + 2 && dy <= -this.height/2 + 2 && !this.yonly && !this.xonly) this.dir = 'nw'
		if(dx <= -this.width/2 + 2 && dy >= this.height/2 - 2 && !this.yonly && !this.xonly) this.dir = 'sw'
		if(dx >= this.width/2 - 2 && dy <= -this.height/2 + 2 && !this.yonly && !this.xonly) this.dir = 'ne'
	}
}

ResizableRectangle.prototype.start = function(){
	this.moving = true;
	this.xmin = this.r.attr("x");
	this.ymin = this.r.attr("y");
	this.r.attr({opacity: 0,cursor:'move'});
}

ResizableRectangle.prototype.move = function(dx,dy){
	x = this.xmin;
	y = this.ymin;
	// Limit to the canvas
	if(!this.yonly){
		x = (this.xmin+dx >= 0) ? this.xmin+dx : 0;	// Limit left
		if(x+this.width >= this.canvas.width) x = this.canvas.width-this.width; // Limit right
	}
	if(!this.xonly){
		y = (this.ymin+dy >= 0) ? this.ymin+dy : 0;	// Limit up
		if(y+this.height >= this.canvas.height) y = this.canvas.height-this.height; // Limit down
	}
	this.r.attr({x:x,y:y});
	this.b.attr({x:x,y:y});
	if(this.ishole) this.hole.attr({path:this.recthole(x,y,this.width,this.height)})
}

ResizableRectangle.prototype.up = function(){
	this.moving = false;
	this.xmin = this.r.attr("x");
	this.ymin = this.r.attr("y");
	this.r.attr({opacity: this.opacity,cursor:'default'});
}

ResizableRectangle.prototype.bstart = function(x,y,e){
	this.sizing = true;
	if(this.dir) this.b.attr({cursor:this.dir+'-resize','stroke-width':this.strokewidth*2});
}

ResizableRectangle.prototype.bmove = function(dx,dy){
	var x = this.xmin;
	var y = this.ymin;
	var w = this.width;
	var h = this.height;
	if(this.dir.indexOf('e') >= 0 && !this.yonly) w += dx;
	if(this.dir.indexOf('w') >= 0 && !this.yonly){
		if(x+dx >= 0){
			if(w-dx > 0){
				x +=  dx;
				w -= dx;
			}else{
				x += w-1;
				w = 1;
			}
		}else{
			w = x+w;
			x = 0;
		}
	}
	if(this.dir.indexOf('n') >= 0 && !this.xonly){
		if(y+dy >= 0){
			if(h-dy > 0){
				y += dy;
				h -= dy;
			}else{
				y += h-1;
				h = 1;
			}
		}else{
			h = y+h;
			y = 0;
		}
	}
	if(this.dir.indexOf('s') >= 0 && !this.xonly) h += dy;
	if(x < 0) x = 0;
	if(w < 0) w = 1;
	if(x+w > this.canvas.width) w = this.canvas.width-x;
	if(y < 0) y = 0;
	if(h < 0) h = 1;
	if(y+h > this.canvas.height) h = this.canvas.height-y;
	this.r.attr({x:x,y:y,width:w,height:h});
	this.b.attr({x:x,y:y,width:w,height:h});
	if(this.ishole) this.hole.attr({path:this.recthole(x,y,w,h)});
}

ResizableRectangle.prototype.bup = function(){
	this.xmin = this.r.attr("x");
	this.ymin = this.r.attr("y");
	this.width = this.r.attr("width");
	this.height = this.r.attr("height");
	this.sizing = false;
	this.b.attr({'stroke-width':this.strokewidth});
}

ResizableRectangle.prototype.recthole = function(x,y,w,h){
	return ["M", 0, 0, "L", this.canvas.width, 0, this.canvas.width, this.canvas.height, 0, this.canvas.height, 0, y, x, y, x, (y+h), (x+w), (y+h), (x+w), y, 0, y, "z"].join(",");
}
Raphael.fn.crosshair = function (rect,cx,cy) {
	this.cx = cx;
	this.cy = cy;
	this.rect = rect;
	var res = this.set();
	res.push(this.path());
	res.update = function(rect,cx,cy){
		var points = ["M", 0, cy*rect.canvas.height, "l", rect.canvas.width, 0, "M", cx*rect.canvas.width, 0, "l", 0, rect.canvas.height];
		this.attr({path: points.join()});
		return this;
	}
	return res.update(rect, cx, cy);
}