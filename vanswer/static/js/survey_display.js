Survey
    .StylesManager
    .applyTheme("modern");

var id = document.getElementById('displayElement').getAttribute('data-id');

var json='';

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

survey.locale = "zh-cn";
survey.mode = 'display';

$("#displayElement").Survey({model: survey});