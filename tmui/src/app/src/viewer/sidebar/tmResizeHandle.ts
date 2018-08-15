// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
angular.module('tmaps.ui')
.directive('tmNoResize', function() {
    return {
        restrict: 'A'
    };
})
.directive('tmResizeHandle', ['$document', function($document) {
    return {
        restrict: 'A',
        scope: false,
        link: function(scope, element, attrs) {

            // TODO: Could get this via some mechanism which allows reuse
            // of the directive. Possibilities: marker directives on the parents
            // or pass the selector via attrs.
            var $section = element.parent();
            var $container = element.parent().parent();

            attrs.$addClass('tm-resize-handle');

            var y;
            var prevY;

            function toPercentage(amount) {
                return amount / $container.height() * 100;
            }

            /**
             * This function calls the chain of elements in direction 'upwards'
             * or 'downwards' requesting each time to shrink the element in y
             * direction.
             * The element will resize as much as it can without going below its
             * minHeight CSS attribute (which should be px-based). The function
             * will return the total amount of pixels that were shrinked, which
             * then can be taken as the amount of pixels that another element
             * can enlarge.
             */
            function shrinkElement(elem, amount, direction) {

                var nextElement = direction === 'upwards' ? elem.prev() : elem.next();
                var nextElementExists = nextElement.length != 0;
                // TODO: Quickfix to check whether the next element has a resize-handle on it.
                // In case it doesn't the element should be shrinkable.
                var isNextElementResizable = false;
                if (nextElementExists) {
                    isNextElementResizable = !nextElement[0].hasAttribute('tm-no-resize');
                }

                var minHeight = parseInt(elem.css('minHeight'));
                var height = elem.height();
                var canShrinkAllTheWay = (height - amount) >= minHeight;

                if (canShrinkAllTheWay) {
                    // If the element can soak up the whole amount, there is no need
                    // to call recurse and request shrinkage of siblings.
                    if (amount > 0) {
                        var newHeightPercentage = toPercentage(height - amount);
                        elem.css('height', newHeightPercentage + '%');
                    }
                    return amount;
                } else {
                    // Either the element is already minimized and it can't shrink
                    // or it can only shrink to some extent. The remaining amount
                    // should be taken from a sibling.
                    var effectiveAmount = height - minHeight;
                    if (effectiveAmount > 0) {

                        var newHeightPercentage = toPercentage(height - effectiveAmount);
                        elem.css('height', newHeightPercentage + '%');
                    }
                    if (nextElementExists && isNextElementResizable) {
                        var shrinkedBySibling =
                            shrinkElement(nextElement, amount - effectiveAmount, direction);
                        return effectiveAmount + shrinkedBySibling;
                    } else {
                        return effectiveAmount;
                    }
                }
            }

            function mousemove(event) {
                // moving down should give a negative y value
                var y = -1 * (event.screenY - prevY);
                prevY = event.screenY;
                var yDelta = Math.abs(y);

                if (y > 0) { // drag direction is upwards
                    if ($section.prev().length != 0) {
                        var allowedAmountToEnlarge = shrinkElement($section.prev(), yDelta, 'upwards');
                        if (allowedAmountToEnlarge > 0) {
                            var newHeightPercentage = toPercentage($section.height() + allowedAmountToEnlarge);
                            $section.css('height', newHeightPercentage + '%');
                        }
                    }
                } else { // drag direction is downwards
                    if ($section.prev().length != 0) {
                        var allowedAmountToEnlarge = shrinkElement($section, yDelta, 'downwards');
                        if (allowedAmountToEnlarge > 0) {
                            var newHeightPercentage = toPercentage($section.prev().height() + allowedAmountToEnlarge);
                            $section.prev().css('height', newHeightPercentage + '%');
                        }
                    }
                }
            }

            function mouseup() {
                $document.off('mousemove', mousemove);
                $document.off('mouseup', mouseup);
            }

            element.on('mousedown', function(event) {
                event.preventDefault();
                prevY = event.screenY;
                $document.on('mousemove', mousemove);
                $document.on('mouseup', mouseup);
            });
        }
    };
}]);
