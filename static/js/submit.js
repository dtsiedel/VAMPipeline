let register_click = () => {
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
}

let poll_outputs = () => {
    $.get('/results', (result) => {
        $('#outputs').empty();
        $('#outputs').append(`<p>Output Files</p>`);
        result.files.forEach((item, index) => {
            let leaf = item.split('/').at(-1);
            let link = `<a href="/outputs/${leaf}">Download</a>`;
            let content = `<div class="output-item">${leaf}. ${link}</div>`;
            $('#outputs').append(content);
        });
    });
}

let register_outputs_poll = () => {
    window.setInterval(poll_outputs, 5000);
}

$('document').ready(() => {
    console.log('Document ready.');
    register_click();
    poll_outputs();
    register_outputs_poll();
});

console.log('Loaded js!')

