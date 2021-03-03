
//isoformat into string
function dateSpan(date) {
  return date;
}

//Main function. Draw your circles.
function makeCircles() {
  //Forget the timeline if there's only one date. Who needs it!?
  if (dates.length < 2) {
    $("#line").hide();
    $("#span").show().text(dates[0]['date']);
    //This is what you really want.
  } else if (dates.length >= 2) {
    //Set day, month and year variables for the math
    var first = Date.parse(dates[0]['date']);
    var last = Date.parse(dates[dates.length - 1]['date']);

    //Integer representation of the last day. The first day is represnted as 0
    var daterange = last - first;

    //Draw first date circle
    $("#line").append(popupContent(0, 0, dateSpan(dates[0])));

    $("#mainCont").append(mainContent(0, dates[0]));

    //Loop through middle dates
    for (i = 1; i < dates.length -1 ; i++) {

      var thisDate = Date.parse(dates[i]['date']);

      //Integer relative to the first and last dates
      var relativeInt = (thisDate - first) / daterange;

      //Draw the date circle
      $("#line").append(popupContent(i, relativeInt*100, dateSpan(dates[i])));
      $("#mainCont").append(mainContent(i, dates[i]));
    }

    //Draw the last date circle
    $("#line").append(popupContent(i,99,dates[dates.length - 1]));
    $("#mainCont").append(mainContent(i, dates[i]));
  }

  $(".circle:first").addClass("active");
}

function popupContent(i, percent, data){
  var obsstatus =  (parseInt(data['num']) > 0) ? 'observed' : "";
  return '<div class="circle '+obsstatus+'" id="circle' + i + '" style="left: ' + percent + '%;"><div class="popupSpan">' + dateSpan(data['date']) +'</div></div>';
}

function mainContent(i, data){
  var html;
  html = '<span id="span' + i + '" class="right">';
  html += '<div class="maindate">Date: '+dateSpan(data['date'])+'<div>';
  html += '<div class="maindate">Observed: '+data['num']+ '</div>';
  html += '<div class="maindate">Type: '+data['type']+ '</div>';
  html += '<div class="maindate">Duration: '+data['duration']/60.+ ' mins</div>';
  html += '<div class="maindate">Location: '+data['location']+'</div>';
  html += '</span>';
  return html
}

function selectDate(selector) {
  $selector = "#" + selector;
  $spanSelector = $selector.replace("circle", "span");
  var current = $selector.replace("circle", "");

  $(".active").removeClass("active");
  $($selector).addClass("active");

  if ($($spanSelector).hasClass("right")) {
    $(".center").removeClass("center").addClass("left")
    $($spanSelector).addClass("center");
    $($spanSelector).removeClass("right")
  } else if ($($spanSelector).hasClass("left")) {
    $(".center").removeClass("center").addClass("right");
    $($spanSelector).addClass("center");
    $($spanSelector).removeClass("left");
  };
};
