console.log('Loaded js!')

$('document').ready(() => {
    console.log('Document ready.');
    $('#submit-button').on('click', () => {
        $.post('/submit',
            {stl_input: $('#stl_input').val(),
             mp4_output: $('#mp4_output').val(),
             method: $('#method').val(),
             fps: $('#fps').val(),
             resolution: $('#resolution').val(),
             iterations: $('#iterations').val(),
            },
            (data) => {
                console.log(data);
            }
        );
    });
});
