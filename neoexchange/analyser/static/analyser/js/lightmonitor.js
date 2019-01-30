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
  blockcandidate = candids[0];

  if (frames.length>0){
    $('#number_images').text(frames.length);
    $('#blink-stop').hide();
    $('#number_images_holder').show();
  }
  $("#cand-submit").hide();

}

function setupImages(){

    console.log("Starting image stuff")
    create_img_stack();

    for(i=0; i<frames.length; i++){
      // Add the URL of each image to the frames array
      var resp = frames[i]['url'];
      // Load image src location into img_Stack
      img_stack[i].src = resp;
      // Preload the image
      var image = new Image();
      image.src = resp;
    };
    // Once all URLs are stored change to the first image
    //changeImage(0, candids[0],allcandidates=true);
    setupAstrometry();
    photo.changeImage(0);
    update_image_index(0);

}

function resetCandidateOptions(){
  stopBlink();
  $("#cand-accept").show()
  $("#cand-reject").show()
  $('.candidate-accept').hide();
  $('#candidate-list').show();
  updateStatus();
  enableBlockCandidateSelector();
  current_candid = undefined;
}

function enableBlockCandidateSelector(){
  if (accepted.length == 1){
    blockcandidate = accepted[0];
  }else if (accepted.length >1){
    $('#block-candidate').show();
  }else{
    $('#block-candidate').hide();
  }
}

function updateBlockCandidate(){
  /* Add select element populated with accepted candidates */
  $('#block-candidate select').html('');
  var cid;
  for (var i = 0, len = accepted.length; i < len; i++) {
    cid = candids.indexOf(String(accepted[i]))+1
    $('#block-candidate select').append('<option value="'+accepted[i]+'">Candidate '+cid+'</option>');
  }
  /* Add a change event to the select elements */
  $('#block-candidate select')
    .change(function () {
    $( "select option:selected" ).each(function() {
      blockcandidate = $( this ).val();
    });
  })
  .change();
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
  updateBlockCandidate();
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

function setZoomCalandBlink(){
  zoomcal = $(this).data('cand_id');
  window.clearTimeout(blinker);
  var checkBox = document.getElementById("blink-check");
  checkBox.checked = true;
  startBlink();

};

function display_info_panel(cindex, ind) {
  var index = image_index(ind);
  // Hide all info tables to start
  $('.coords-table').hide();
  $('.candidate-row').hide();
  // Only show info tables for current index
  $('.candidate-'+cindex).show();
  $('.candidate-'+cindex +' '+'#img-coords-'+index).show();
  $('.candidate-'+cindex +' '+'#img-skycoords-'+index).show();
}

function blinkCandidate(ind) {
  stopBlink();
  startBlink(ind, false);
  $('#candidate-list').hide();
  $('.candidate-accept').show();

  $("#cand-accept").data('cand_id', ind);
  $("#cand-reject").data('cand_id', ind);
}


function create_img_stack(){
  // Setup a blank img_stack
  for (j=0;j<frames.length;j++){
    img_stack.push({coords: new Array(),src:''});
  }
  for (i=0;i<candidates.length;i++){
    for (j=0;j<frames.length;j++){
      img_stack[j].coords.push({x:candidates[i].coords[j].x/img_scale.x, y: candidates[i].coords[j].y/img_scale.y});
      //img_stack[j].coords.push({x:i*200, y:100+10*i});
    }
  }
}


function get_images(frame, options=''){

    $.get({url:'https://thumbnails.lco.global/'+frame.img+'/'+options,
          headers: {'Authorization': 'Token '+archive_token},
          dataType: 'json',
          contentType: 'application/json'}
        )
      .success(function(data){
        frame['url'] = data['url'];
      })
      .fail(function(data){
        console.log("FAILED to get thumbnail");
      })

    return frame
  }

  function changeBlink() {
    var checkBox = document.getElementById("blink-check");

    if (checkBox.checked == true){
      startBlink();
    } else {
      stopBlink();
    }
  }

  function setupAstrometry(){

    photo = new Astrometry({id:'astrometric',src:img_stack[0].src,width:$('#middle').outerWidth(),calibrator:{label:'Candidate '}, candidates: img_stack[0].coords,zoom:3,img_stack:img_stack});

  };

  function startBlink() {
    var index=0;
    blinker = setInterval(function() {
      index++;
      photo.nextImage (index, zoomcal);
      display_info_panel(zoomcal, index);
      update_image_index(index);
    }, 500);
    $('#blink-stop').show();
    $('#blink-start').hide();
  }

  function update_image_index(ind){
    var index = image_index(ind);
    $('#current_image_index').text(index+1)
  }

  function stopBlink() {
    window.clearTimeout(blinker);
    $('#blink-stop').hide();
    $('#blink-start').show();
  }

function resetZoomLevel(){
  zoomcal = undefined;
  photo.sizer[0].updateZoom(1);
  photo.sizer[0].zoom.css({'display':'none'});
  photo.sizer[0].redraw();
}

function image_index(ind) {
  if (typeof(ind) == 'undefined') {
    index = 0;
  } else {
    index = ind % img_stack.length;
  }
  return index
}
