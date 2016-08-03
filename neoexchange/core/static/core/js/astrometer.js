// Astrometer for NEO exchange


function setUp(){
  stage = new createjs.Stage("imgCanvas");
  ministage = new createjs.Stage("zoomCanvas");
  if (frames.length>0){
    index = 0;
  }
  changeImage(index);

}

function addCircle(x, y, r, fill, name, draggable) {
   var circle = new createjs.Shape();
   circle.graphics.beginFill(fill).drawCircle(0, 0, r);
   circle.x = x;
   circle.y = y;
   circle.alpha = 0.2;
   circle.name = name;
   if (draggable==true){
     circle.on("pressmove", drag);
     circle.alpha = 0.5;
   }
   stage.addChild(circle);
  }


function drag(evt) {
    evt.target.x = evt.stageX;
    evt.target.y = evt.stageY;
    stage.update();
    updateTarget(evt.currentTarget.name, evt.currentTarget.x, evt.currentTarget.y);
    zoomImage(evt.currentTarget.x, evt.currentTarget.y);
}

function updateTarget(name, x, y) {
  // Identify correct target
  var target_name = name.split("_");
  var target_id;
  if (target_name.length != 2){
    return false;
  } else {
    target_id = target_name[1];
  }
  var target = frames[currentindex].targets[target_id];
  target.x = x;
  target.y = y;
}

function startBlink() {
  blinker = setInterval(function() {
    index++;
    changeImage (index);
  }, 500);
}

function stopBlink() {
  clearInterval(blinker);
}

function zoomImage(x,y){
  var width = 200;
  var height = 200;
  ministage.removeAllChildren();
  mini_img = img_holder.clone()
  mini_img.scaleX=2;
  mini_img.scaleY=2;
  mini_img.sourceRect = new createjs.Rectangle(x-width/2,y-width/2,width,height);
  ministage.addChild(mini_img);
  ministage.update();
}

function changeImage(index) {
  //
  //
  if (isNaN(index)) {
    currentindex = Math.floor(Math.random() * frames.length);
  } else {
    currentindex = index % frames.length;
  }
  // Remove everything already on the stage
  stage.removeAllChildren();

  frame_container = '#imgCanvas'
  fetch_thumbnail(frames[currentindex].img, frame_container, img_params);
  image_url = $('#imgCanvas').attr('src')
  console.log(image_url)

  img_holder = new createjs.Bitmap(image_url);
  // Duplicate this image on to the mini canvas
  zoomImage(500,100);
  // Scale the image to fit inside canvas
  img_holder.scaleX = 0.6;
  img_holder.scaleY = 0.6;
  stage.addChild(img_holder);

  // Add background sources
  for (var i=0; i <frames[currentindex].sources.length;i++) {
    source = frames[currentindex].sources[i];
    name = "source_" + i;
    addCircle(source.x, source.y, point_size, "#e74c3c", name, false);
  }
  // Add targets
  for (var i=0; i <frames[currentindex].targets.length;i++) {
    target = frames[currentindex].targets[i];
    name = "target_" + i;
    addCircle(target.x, target.y, point_size, "#58FA58", name, true);
  }
  stage.update();

  // Update the name of the current frame on the page
  $("#frame_id_holder").text(frames[currentindex].img);

}

function loadThumbnails(frames){
  for(var i in frames)
   {
     var frame = frames[i] ;
      var thumbnail_container;
      thumbnail_container = $('ul.observations');
      link_url = "http://lcogt.net/observations/frame/"+frame.img+"/"
      var thumb_html = '<li class="thumb"><a href="#main" class="image_switch" data-imgsrc="'+frame.img+'"><img src="https://lcogt.net/files/no-image_120.png" id="frame-'+frame.img+'"></a></li>';

      thumbnail_container.append(thumb_html);
      fetch_thumbnail(frame.img,'.observations img#frame-'+frame.img);
    }
}

function fetch_thumbnail(frameid, frame_container,options=''){
  var url = "https://thumbnails.lcogt.net/" + frameid +"/" +options;
  var resp;
  $.get(url, function(data){
      resp = data.url;
      $(frame_container).attr('src', resp);
  });
}
