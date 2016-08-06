// Astrometer for NEO exchange


function setUp(){

  stage = new createjs.Stage("imgCanvas");
  ministage = new createjs.Stage("zoomCanvas");
  if (frames.length>0){
    index = 0;
  }

  changeImage(index);

  $('#number_images').text(frames.length);
  $('#blink-stop').hide();

}

function nextImage() {
  var next_i = index +1;
  if (next_i <= frames.length){
    changeImage(next_i);
  } else {
    console.log('Final Image')
  }
}

function prevImage() {
  var prev_i = index -1;
  if (prev_i > 0){
    changeImage(prev_i);
  } else {
    console.log('First Image')
  }
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
  $('#blink-stop').show();
  $('#blink-start').hide();
}

function stopBlink() {
  clearInterval(blinker);
  $('#blink-stop').hide();
  $('#blink-start').show();
}

function zoomImage(x,y){
  var width = 200;
  var height = 200;
  var x_i = 5/3*x;
  var y_i = 5/3*y;
  ministage.removeAllChildren();
  mini_img = img_holder.clone();
  mini_img.scaleX=2;
  mini_img.scaleY=2;
  mini_img.sourceRect = new createjs.Rectangle(x_i-width/4,y_i-height/4,width,height);
  ministage.addChild(mini_img);
  ministage.update();
}

function handleLoad(event) {
  stage.update();
}

function changeImage(ind) {
  //
  //
  if (typeof(ind) == 'undefined') {
    index = 0;
  } else {
    index = ind % frames.length;
  }
  // Remove everything already on the stage
  stage.removeAllChildren();

  // Change label
  $('#current_image_index').text(index+1);
  frame_container = '#imgCanvas'
  image_url = frames[index].url;

  if (typeof(image_url) == 'undefined') {
    $('#image-loading').show();
    return;
  }else{
    $('#image-loading').hide();
  }

  img_holder = new createjs.Bitmap(image_url);
  // Update the stage when the image data has loaded
  img_holder.image.onload = handleLoad;
  // Duplicate this image on to the mini canvas
  zoomImage(500,100);
  // Scale the image to fit inside canvas
  img_holder.scaleX = 0.6;
  img_holder.scaleY = 0.6;
  stage.addChild(img_holder);

  // Add background sources
  // for (var i=0; i <frames[index].sources.length;i++) {
  //   source = frames[index].sources[i];
  //   name = "source_" + i;
  //   addCircle(source.x, source.y, point_size, "#e74c3c", name, false);
  // }
  // Add targets
  for (var i=0; i <frames[index].targets.length;i++) {
    target = frames[index].targets[i];
    name = "target_" + i;
    addCircle(target.x, target.y, point_size, "#58FA58", name, true);
  }
  stage.update();

}

function loadThumbnails(frames){
  for(var i in frames)
   {
     var frame = frames[i];
     fetch_thumbnail(frame, img_params)
    }
  return
}

function fetch_thumbnail(frame, options=''){
  var url = "https://thumbnails.lcogt.net/" + frame.img +"/" +options;
  $.get(url, function(data){
      var resp = data.url;
      frame['url'] = resp;
      // Preload the image
      var image = new Image()
      image.src = resp;
  });
}
