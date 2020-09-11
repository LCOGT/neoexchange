const AJAX_POLL_INTERVAL = 1000;  // in milliseconds

/*
 * Display an error message after a failed AJAX request
 */
function showError(msg) {
    // TODO: show the error in the UI
    throw msg;
}

/*
 * Return a string representation of a date given as a UNIX timestamp
 */
function getDateString(timestamp) {
    return new Date(timestamp * 1000).toLocaleString();
}

function capitaliseFirst(str) {
    return str[0].toUpperCase() + str.substr(1);
}

function truncate(str, max_length) {
    if (str.length <= max_length) {
        return str;
    }
    return str.substr(0, max_length - 3) + '...';
}
