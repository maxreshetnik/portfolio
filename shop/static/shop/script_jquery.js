$( document ).ready(function() {
    let isMouseClick = false;
    $(".rating-item")
        .focus(function() {
            if (isMouseClick) {
                this.blur();
                isMouseClick = false;
            };
        })
        .click(function() {
            if ( $('#loginModalButton').length ) {
                console.log("User not authenticated.");
                $('#loginModalButton').get(0).click();
                return false;
            };
            console.log('Submitting a rating form using ajax');
            sendAjaxForm(this.form.id, ratingAjaxSuccess, ratingAjaxError);
		});
    $(".rating > label")
        .mousedown(function() {
            isMouseClick = true;
        })
        .mouseup(function() {
            isMouseClick = true;
        });
});

function ratingAjaxSuccess(response, form_id) {
    console.log(response.success);
    $( '#' + form_id + " .rating label[class~=text-secondary]" )
        .removeClass("text-secondary bi-star-fill")
        .addClass("text-warning bi-star");
    $( '#' + form_id + ' .rating-avg' ).html(
        response.rating_avg.toFixed(1) + ' (' + response.rating_count + ')'
    );
    $('#ajax-success')
        .html(response.success).removeClass("d-none")
        .show().delay( 3.0*1000 ).fadeOut( 800 );
}

function ratingAjaxError(response, form_id) {
    const errors = JSON.parse(response.responseJSON.errors);
    console.log('--Errors--');
    $.each(errors, function (field, data) {
        $.each(data, function(index,error) {
            console.log(field + ': ' + error.message + ', code: ' + error.code);
            if (field == 'point') {
                $( '#' + form_id + ' .rating-item' )
                    .prop('checked', false);
                $( '#' + form_id + ' .rating-error' )
                    .text(error.message).show()
                    .delay( 10.0*1000 ).fadeOut( 800 );
            } else {
                $('#ajax-error')
                    .text(error.message).removeClass("d-none")
                    .show().delay( 10.0*1000 ).fadeOut( 800 );
            }
        });
    });
}

function sendAjaxForm(form_id, success_func, error_func) {
    const form = $( '#' + form_id );
    $.ajax({
        url:     form.attr('data-ajax-url') || form.attr('action'),
        type:    form.attr('method'),
        data:    form.serialize(),
 	}).done(function(response) {
        success_func(response, form_id);
    }).fail(function(response) {
        error_func(response, form_id);
    });
}
