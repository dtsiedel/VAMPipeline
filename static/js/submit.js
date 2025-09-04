let poll_interval = 2;

let img_for_id = (id) => {
    return `<img src="/thumbs/${id}.svg" width="50 height="50">`
};

let div_for_item = (img, item) => {
    // Used for running/queued display
    return `<div class="running-item">${img} ID: ${item.id} Iters: ${item.iters} Resolution: ${item.resolution} FPS: ${item.fps} Method: ${item.method}</div>`;
};

let register_click = () => {
    $('#submit-button').on('click', () => {
        let has_file = $('#file-input').get(0).files.length != 0;
        if (!has_file) {
            return;
        }
        $.ajax({
            url: '/upload',
            type: 'POST',

            data: new FormData($('form')[0]),

            // Tell jQuery not to process data or worry about content-type
            cache: false,
            contentType: false,
            processData: false,
            // On successful upload, submit other form fields
            success: (result) => {
                let id = result.id;
                console.log(`Submit succeeded with ${id}`)

                $.post('/submit',
                    {uuid: id,
                     method: $('#method').val(),
                     fps: $('#fps').val(),
                     resolution: $('#resolution').val(),
                     iterations: $('#iterations').val(),
                    }
                );
            },
            fail: (result) => {
                let id = result.id;
                console.log(`Submit failed with ${id}`)
            }
        });
    });
};

let poll_outputs = () => {
    $.get('/results', (result) => {
        $('#outputs').empty();
        $('#outputs').append(`<p>Output Files</p>`);
        result.files.forEach((item, index) => {
            let leaf = item.split('/').at(-1);
            let img = img_for_id(leaf.split('.')[0])
            let link = `<a href="/outputs/${leaf}">${leaf}</a>`;
            let content = `<div class="output-item">${img} ${link}</div>`;
            $('#outputs').append(content);
        });
    });
};

let poll_queued = () => {
    $.get('/queued', (result) => {
        $('#queued').empty();
        $('#queued').append(`<p>Queued Jobs</p>`);
        result.queued.forEach((item, index) => {
            let img = img_for_id(item.id);
            let content = div_for_item(img, item);
            $('#queued').append(content);
        });
    });
};

let poll_running = () => {
    $.get('/running', (result) => {
        $('#running').empty();
        $('#running').append(`<p>Running Jobs</p>`);
        result.running.forEach((item, index) => {
            let img = img_for_id(item.id);
            let content = div_for_item(img, item);
            $('#running').append(content);
        });
    });
};

let register_outputs_poll = () => { window.setInterval(poll_outputs, poll_interval * 1000); }
let register_queued_poll = () => { window.setInterval(poll_queued, poll_interval * 1000); }
let register_running_poll = () => { window.setInterval(poll_running, poll_interval * 1000); }

$('document').ready(() => {
    console.log('Document ready.');
    register_click();
    poll_outputs();
    register_outputs_poll();
    poll_queued();
    register_queued_poll();
    poll_running();
    register_running_poll();
});

console.log('Loaded js!')

