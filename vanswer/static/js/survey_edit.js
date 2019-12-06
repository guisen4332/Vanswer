SurveyCreator
    .localization
    .currentLocale = "zh-cn";

SurveyCreator
    .StylesManager
    .applyTheme("default");


var creatorOptions = {
    questionTypes: ["radiogroup", "checkbox", "dropdown", "rating"],
    showJSONEditorTab: true,
    // showEmbededSurveyTab: true,
    showPropertyGrid: false,
    showState: true,
    useTabsInElementEditor: true,
    // isAutoSave: true
};

var creator = new SurveyCreator.SurveyCreator("creatorElement", creatorOptions);

creator
    .onCanShowProperty
    .add(function (sender, options) {
        if (options.obj.getType() == "survey") {
            options.canShow = options.property.name == "title";
        }
    });


function extend(des, src, override){
    if(src instanceof Array){
        for(var i = 0, len = src.length; i < len; i++)
            extend(des, src[i], override);
    }
    for( var i in src){
        if(override || !(i in des)){
            des[i] = src[i];
        }
    }
    return des;
}

var title = {"title": document . getElementById('creatorElement').getAttribute('data-name')};

var id = document . getElementById('creatorElement').getAttribute('data-id')

// var text = "{ title: \'标题示例\', pages: [{ name:\'page1\', questions: [{ type: \'text\', name:\"q1\"}]}]}";
// creator.text = JSON.stringify(extend({},[title, eval('(' + text + ')')]));

creator.text = JSON.stringify(title);

$.ajax({
    url: "/survey_content",
    type: "GET",
    data:{ "id": id },
    dataType: "json",
    success: function (data) {
        if (!jQuery.isEmptyObject(data)) {
            creator.text = data;
        }
    }
});

function isJSON(str){
    if (typeof str == 'string') {
        try {
            var obj = JSON.parse(str);
            if (typeof obj == 'object' && obj) {
                console.log('是JSON');
                return true;
            } else {
                return false;
            }
        } catch (e) {
            console.log('error：' + str + '!!!' + e);
            return false;
        }
    }
}

creator.saveSurveyFunc = function (saveNo, callback) {
    console.log(creator.text)
	console.log(typeof creator.text)
    isJSON(creator.text)
    $.ajax({
        url: "/save_survey",
        type: "POST",
		contentType: 'application/json; charset=UTF-8',
		data: JSON.stringify({surveyId: id, surveyText : creator.text}),
        success: function (data) {
            callback(saveNo, true);
        },
        error: function (xhr, ajaxOptions, thrownError) {
            callback(saveNo, false);
            // alert(thrownError);
        }
    });
}

