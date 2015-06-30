// jquery.typewriter.js
//
// Doug Thomas, LCOGT
//

function start_typing(){
    console.log('start_typing');
    console.log($.fn.typewriter.elements);
    // type serially, one element at a time
    if($.fn.typewriter.typing == null){
        var element = $.fn.typewriter.elements.shift();
        if(element && $(element).is(':visible')){
            $.fn.typewriter.typing = setInterval(
                function(){
                    if (element.typewriter.indice < element.typewriter.elementStr.length) {
                        $(element).append(element.typewriter.elementStr[element.typewriter.indice++]);
                    }else{
                        clearInterval($.fn.typewriter.typing);
                        $.fn.typewriter.typing = null;
                        start_typing(); // now type the next element
                    }
                },
                element.typewriter.dataSpeed,
                element
            );
        }
    }
}

(function($, w, d, undefined) {

    function typewriter() {

        var self = this;

        function init(element, options) {
            self.indice = 0;
            self.options = $.extend( {}, $.fn.typewriter.defaults, options );
            var $currentElement = $(element);
            self.elementStr = $currentElement.text().replace(/\s+/g, ' ');
            self.dataSpeed  = $currentElement.data("speed") || self.options.speed;

            $currentElement.empty();
            $currentElement.css('display','block');
            element.typewriter = self;
            $.fn.typewriter.elements.push(element);
            start_typing();
        }

        return {
            init: init
        }
    }

    // Plugin jQuery
    $.fn.typewriter = function(options) {
        return this.each(function () {
            var writer =  new typewriter();
            writer.init(this, options);
            //$.data( this, 'typewriter', writer);
        });
    };

    $.fn.typewriter.defaults = {
        speed : 300
    };

    $.fn.typewriter.elements = [];

    $.fn.typewriter.typing = null;

})(jQuery, window, document);
