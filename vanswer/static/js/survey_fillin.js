Survey
    .StylesManager
    .applyTheme("modern");

var json='';

var id = document.getElementById('fillinElement').getAttribute('data-id');

$.ajax({
    url: "/survey_content",
    type: "GET",
    data:{ "id": id },
    dataType: "json",
    async:false,
    success: function (data) {
        if (!jQuery.isEmptyObject(data)) {
            console.log(data)
            json = data;
        }
    }
});

survey = new Survey.Model(json);

survey.locale = "zh-cn"

$("#fillinElement").Survey({
    model: survey,
    onComplete: sendDataToServer
});

function sendDataToServer(survey) {
    console.log(survey.data)
    var  resultAsString = JSON.stringify(survey.data)
    console.log(resultAsString)
    $.ajax({
        url: "/save_result"+'?id='+id,
        type: "POST",
        contentType: 'application/json; charset=UTF-8',
        data: resultAsString,
        success: function (data) {
            alert("提交成功！")
        },
        error: function (xhr, ajaxOptions, thrownError) {
            alert("提交失败，请重新尝试")
        }
    });
}