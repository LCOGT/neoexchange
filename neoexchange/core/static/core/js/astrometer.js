// Astrometer for NEO exchange

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}


function setUp(){

  $.ajaxSetup({
      beforeSend: function(xhr, settings) {
          if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
              xhr.setRequestHeader("X-CSRFToken", csrftoken);
          }
      }
  });
  for (var i = 0; i < candidates.length; i++) {
    candids.push(candidates[i]['id']);
  }

  stage = new createjs.Stage("imgCanvas");
  ministage = new createjs.Stage("zoomCanvas");
  if (frames.length>0){
    $('#number_images').text(frames.length);
    $('#blink-stop').hide();
  }
  $("#cand-submit").hide();
  loadCandidates(candidates);

}

function resetCandidateOptions(){
  stopBlink();
  $("#cand-accept").show()
  $("#cand-reject").show()
  $('.candidate-accept').hide();
  $('#candidate-list').show();
  updateStatus();
}

function updateStatus(){
  $(".block-status-icon").hide();
  if (accepted.length>0) {
    $("#cand-submit").show();
  } else {
    $("#cand-submit").hide();
  }
  $(".block-status-icon").hide();
  for (var i = 0, len = accepted.length; i < len; i++) {
    $("#cand-"+accepted[i]+"-accept").show();
    $("#cand-"+accepted[i]+"-reject").hide();
  }
  for (var i = 0, len = rejected.length; i < len; i++) {
    $("#cand-"+rejected[i]+"-accept").hide();
    $("#cand-"+rejected[i]+"-reject").show();  }
}

function nextImage() {
  var next_i = index +1;
  if (next_i <= frames.length){
    changeImage(next_i);
  }
}

function prevImage() {
  var prev_i = index -1;
  if (prev_i >= 0){
    changeImage(prev_i);
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
    // updateTarget(evt.currentTarget.name, evt.currentTarget.x, evt.currentTarget.y);
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
  console.log(target_id)
  var target = frames[index].candidates[target_id];
  target.x = x;
  target.y = y;
}

function acceptCandidate(cand_id){
  // Add the candidate ID to accepted array only if it is not already there
  // Show the tick on the candidate line
  $("#cand-accept").show()
  $("#cand-reject").hide()
  if (rejected.indexOf(cand_id) > -1){
    var index = rejected.indexOf(cand_id);
    if (index > -1) {
      rejected.splice(index, 1);
    }
  }
  if (accepted.indexOf(cand_id) == -1){
    accepted.push(cand_id);
  }
}

function rejectCandidate(cand_id){
  // Remove candidate ID from accepted array if it was there
  // Show the X on the candidate line
  $("#cand-accept").hide()
  $("#cand-reject").show()
  if (accepted.indexOf(cand_id) > -1){
    var index = accepted.indexOf(cand_id);
    if (index > -1) {
      accepted.splice(index, 1);
    }
  }
  if (rejected.indexOf(cand_id) == -1){
    rejected.push(cand_id);
  }
}

function startBlink(cand_index=0, allcandidates=false) {
  blinker = setInterval(function() {
    index++;
    changeImage (index, cand_index, allcandidates);
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

function loadCandidates(candidates){
  for (var i=0;i< candidates.length; i++){
    var cid = candidates[i]['id']
    var cand_html = "<li class='grey-dark'>";
    cand_html += "<span class='candidate'>";
    cand_html +="<span data-cand_id='"+cid+"' class='candidate-select'>";
    cand_html +="<span class='block-status-item' ><i class='fa fa-refresh'></i></span>";
    cand_html += "<span class='block-status-item'>Blink Candidate "+(i+1)+"</span></span>";
    cand_html +="<span class='block-status-item block-status-icon text-red' id='cand-"+cid+"-reject' style='display:none;'><i class='fa fa-ban'></i></span>"
    cand_html +="<span class='block-status-item block-status-icon text-green' id='cand-"+cid+"-accept' style='display:none;'><i class='fa fa-check'></i></span>"
    cand_html +="</span>";
    cand_html += "</li>";
    $('#candidate-list').append(cand_html);
  }
}

function changeImage(ind, cand_index=0, allcandidates=false) {
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

  if (allcandidates){
    for (var i=0; i <candidates.length;i++) {
      target = candidates[i].coords[ind-1];
      name = "target_" + i;
      addCircle(target.x/image_scale, target.y/image_scale, point_size, "#58FA58", name, true);
    }
  }else{
    var id = candids.indexOf(String(cand_index))
    target = candidates[id].coords[ind-1];
    name = "target_" + cand_index;
    addCircle(target.x/image_scale, target.y/image_scale, point_size, "#58FA58", name, true);
    zoomImage(target.x/image_scale, target.y/image_scale);
  }
  stage.update();

}

function loadThumbnails(frames){
  var requests = Array();
  for(var i in frames)
   {
     var frame = frames[i];
     requests.push($.get("https://thumbnails.lco.global/" + frame.img +"/" +img_params));
    }
  // Package and display the images once all the AJAX requests have finished
  var defer = $.when.apply($, requests);
  defer.done(function(){
    $.each(arguments, function(index, data){
      // Add the URL of each image to the frames array
      var resp = data[0].url;
      frames[index]['url'] = resp;
      // Preload the image
      var image = new Image()
      image.src = resp;
    });
    // Once all URLs are stored change to the first image
    changeImage(0);
  });
  return
}

function fetch_thumbnail(frame, options=''){
  var url = "https://thumbnails.lco.global/" + frame.img +"/" +options;
  $.get(url, function(data){
      var resp = data.url;
      frame['url'] = resp;
      // Preload the image
      var image = new Image()
      image.src = resp;
  });
}
