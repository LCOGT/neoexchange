const URL = '/api/pipeline/logs/' + PIPELINE_PROCESS_PK + '/';
var $CREATED      = $('#process-created');
var $STATUS       = $('#process-status');
var $FINISHED     = $('#process-finished');
var $OUTPUTS      = $('#process-outputs-link');
var $FOLLOW_LOGS  = $('#follow-logs')[0];
var $LOGS_WRAPPER = $('pre.logs');
var $LOGS         = $LOGS_WRAPPER.find('code');

window.setInterval(function() {
    $.get(URL, function(data) {
        $CREATED.text(getDateString(data.created));

        var status_text = capitaliseFirst(data.status);
        if (data.status === 'failed' && data.failure_message) {
            status_text += ` (${data.failure_message})`;
        }
        $STATUS.text(status_text);

        var finished_text = data.terminal_timestamp ? getDateString(data.terminal_timestamp) : 'N/A';
        $FINISHED.text(finished_text);

        if (data.group_name && data.group_url) {
            var $link = $('<a>');
            $link.attr('href', data.group_url);
            $link.attr('title', 'View the outputs of this process');
            $link.text(truncate(data.group_name, 20));
            $OUTPUTS.html('');
            $OUTPUTS.append($link);
        }
        else {
            $OUTPUTS.text('N/A');
        }

        $LOGS.text(data.logs);
        // Scroll logs element if the user wishes
        if ($FOLLOW_LOGS.checked) {
            $LOGS_WRAPPER.animate({
                'scrollTop': $LOGS.height(),
            }, 1000, 'linear');
        }
    }, 'json').fail(function() {
        showError('Failed to retrieve process information');
    });
}, AJAX_POLL_INTERVAL);
