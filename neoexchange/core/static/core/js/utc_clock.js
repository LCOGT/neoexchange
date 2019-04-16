var doClock = (function () {

  // Helper
  function z(n){return (n<10?'0':'') + n}

  return function() {

    // Create a new Date object each time so
    // it doesn't matter if a second or more is skipped
    var now = new Date();

    // write clock to document, values are UTC
    document.getElementById('clock').innerHTML = now.getFullYear()   + '-' +
                                                 z(now.getMonth()+1) + '-' +
                                                 z(now.getUTCDate())    + ' ' +
                                                 z(now.getUTCHours())   + ':' +
                                                 z(now.getUTCMinutes()) + ' UTC';
    // Run again just after next full second
    setTimeout(doClock, 1020 - now.getMilliseconds());
  };
}());

window.onload = doClock;