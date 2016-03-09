angular.module('tmaps.ui')
/*
 * ! THIS ELEMENT IS A WORKAROUND !
 *
 * Position an element with 'position' == 'fixed' according to it's parent
 * element.
 * CSS attributes 'left' 'right' 'top' etc. are interpreted as relative offsets
 * to the parent element (regardless of what position attribute that parent
 * element has).
 * This directive is hacky but necessary to display divs contained in
 * li-elements that reside in containers with overflow hidden.
 */
.directive('tmAttachToParent', function() {
    return {
        restrict: 'EA',
        link: function($scope, $elem, $attr) {

            var left = $elem.css('left') == 'auto' ? 0 : parseInt($elem.css('left'));
            var right = $elem.css('right') == 'auto' ? 0 : parseInt($elem.css('right'));
            var top = $elem.css('top') == 'auto' ? 0 : parseInt($elem.css('top'));
            var bottom = $elem.css('bottom') == 'auto' ? 0 : parseInt($elem.css('bottom'));
            var width = parseInt($elem.css('width'));

            if (!width) {
                // throw new Error('You must specify a width to use this directive!');
                console.log('You must specify a width to use this directive!');
            }

            var $parent = $elem.parent();

            // TODO: Note that this code has to be adjusted somewhat if the divs
            // should also be shown to the right of an element.
            function updatePosition() {
                var parentPos = $parent.offset();
                $elem.css({
                    left: parentPos.left - right + left - width,
                    top: parentPos.top - bottom + top
                });
            }

            $(window).resize(function() {
                updatePosition();
            });

            // The parent item is a clickable button that should pop out the div
            // to which this directive is attached. The positions may have
            // changed, therefore they should be updated before showing the div.
            $parent.click(function() {
                updatePosition();
            });

            updatePosition();
        }
    };
});
