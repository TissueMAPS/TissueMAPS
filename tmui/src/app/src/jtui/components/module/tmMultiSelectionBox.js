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
//angular.module('jtui.module')
///**
// * These directives provide box-like structure for listing selectable items such as layers.
// * These items  are represented as tab-like buttons with a popup window that can be
// * displayed by pressed the arrow-button on the tab's left.
// *
// * In addition, several buttons can be added at the bottom of the list. These
// * buttons may provide functionality that involves the currently selected layers
// * in this particular selection box.
// *
// * The top-most directive needs two attributes: 'items' which corresponds to
// * the model to display using ngRepeat and 'by-name' which is the name with which
// * the individual items in `items` will be accessible in the content & popup.
// *
// * Usage:
// *
// * <tm-multi-selection-box items="someOtherCtrl.layers" by-name="layer">
// *   <tm-selectable-tabs>
// *
// *   <!-- Where someOtherCtrl provides the list of layer objects. -->
// *
// *   <!-- The following directives may also have an ng-controller on them. -->
// *
// *    <tm-selectable-tab>
// *      <tm-selectable-tab-popup>
// *
// *        Stuff to display in the popup window
// *        Has access to the item in the form of $scope.item or
// *        $scope.{{ name provided to tmMultiSelectionBox }}
// *
// *        In addition:
// *            - $scope.selectionBox.getSelectedItems() will return the items
// *              that were selected by clicking on tabs while holding shift.
// *
// *      </tm-selectable-tab-popup>
// *      <tm-selectable-tab-content>
// *
// *        Stuff to display in the content window
// *        Has the same access as the content of tm-selectable-tab-popup.
// *
// *      </tm-selectable-tab-content>
// *    </tm-selectable-tab>
// *   </tm-selectable-tabs>
// *
// *   <tm-multi-selection-controls ng-controller="MyButtonCtrl as btn">
// *
// *   The content of this element as well as MyButtonCtrl have
// *   access to selectionBox and its 'getSelectedItems' method.
// *
// *    <button ng-click="btn.button1()"> Button 1 </button>
// *    <button ng-click="...">           Button 2 </button>
// *    <button ng-click="...">           Button 3 </button>
// *
// *   </tm-multi-selection-controls>
// *
// * </tm-multi-selection-box>
// *
// */
//.directive('tmMultiSelectionBox', function() {
//    var template =
//        '<div class="tm-multi-selection-box">' +
//        '</div>';
//    return {
//        template: template,
//        restrict: 'E',
//        require: 'tmMultiSelectionBox',
//        controller: 'MultiSelectionBoxCtrl',
//        bindToController: true,
//        controllerAs: 'selectionBox', // required to bind scope props to instance
//        transclude: true,
//        scope: {
//            items: '=',
//            byName: '='
//        },
//        link: function(scope, elem, attrs, ctrl, transclude) {

//            // Same as ng-transclude but add the ctrl instance
//            // to the scope, s.t. it is accessible by the child ctrls.
//            var innerScope = scope.$parent.$new();
//            innerScope.selectionBox = ctrl;

//            transclude(innerScope, function(clone) {
//                elem.empty();
//                elem.append(clone);
//                elem.on('$destroy', function() {
//                    innerScope.$destroy();
//                });
//            });
//        }
//    };
//})
//.directive('tmMultiSelectionControls', function() {
//    /**
//     * All buttons added to this directive have access to the selected layers.
//     *
//     * <tm-multi-selection-controls>
//     *   <button ng-controller="myButtonCtrl1"/>
//     *   <button ng-controller="myButtonCtrl2"/>
//     *   ...
//     * </tm-multi-selection-controls>
//     */
//    var template =
//        '<div class="tm-multi-selection-controls" inject>' +
//        '</div>';
//    return {
//        template: template,
//        restrict: 'E',
//        transclude: true
//    };
//})
//.directive('tmSelectableTabs', ['uiState', function(uiState) {
//    // Inject will transclude the DOM that is wrapped inside of this directive
//    // into the ng-repeat. It will also set up the transclusion scope in such a way
//    // that it is linked to the scope provided by ngRepeat.
//    var template =
//        '<div class="tm-selectable-tabs" perfect-scrollbar>' +
//            '<ul ui-sortable="{axis: \'y\'}"' +
//               ' ng-model="selectionBox.items" >' +
//                '<li ng-repeat="item in selectionBox.items" ' +
//                     'class="tm-selectable-tab-li" inject tm-rename-item>' +
//                '</li>' +
//            '</ul>' +
//        '</div>';

//    return {
//        transclude: true,
//        template: template,
//        restrict: 'E'
//    };
//}])
//.directive('tmSelectableTab', [function() {
//    return {
//        require: ['tmSelectableTab'],
//        restrict: 'E',
//        controller: 'SelectableTabCtrl',
//        // The popup and content may access this ctrl via '$scope.tab'.
//        controllerAs: 'tab'
//    };
//}])
//.directive('tmSelectableTabPopup', function() {
//    var template =
//        '<div class="tm-selectable-tab-popup-button show-additional-layer-settings"' +
//             ' ng-click="tab.showPopupWindow()"' +
//             ' tm-stop-click>' +

//          '<i class="fa fa-chevron-left"></i>' +

//          '<div class="tm-selectable-tab-popup-window additional-layer-settings"' +
//               ' ng-mouseleave="tab.closePopupWindow()"' +
//               ' ng-show="tab.isPopupWindowOpen"' +
//               ' tm-attach-to-parent inject>' +
//           '</div>' +
//        '</div>';

//    return {
//        template: template,
//        transclude: true
//    };
//})
//.directive('tmSelectableTabContent', function() {
//    var template =
//        '<div class="tm-selectable-tab-content"' +
//           ' ng-class="{selected: tab.isSelected}"' +
//           ' ng-click="tab.selectTab()"' +
//           ' ng-mouseover="tab.mouseover = true"' +
//           ' ng-mouseleave="tab.mouseover = false" inject>' +
//        '</div>';

//    return {
//        template: template,
//        transclude: true
//    };
//})
///**
// * Needed to transclude stuff into ng-repeat the way we need to.
// * From: https://github.com/angular/angular.js/issues/7874#issuecomment-47647528
// */
//.directive('tmRenameItem', function() {
//    return {
//        require: '^^tmMultiSelectionBox',
//        // This directive has to be linked before `inject`.
//        // Execution order is reversed in linking phase, therefore
//        // => negative priorities mean earlier linking (inject has 0).
//        priority: -1,
//        link: function(scope, element, attrs, controller) {
//            // Alias the item under a new name
//            if (controller.byName) {
//                scope[controller.byName] = scope.item;
//            }
//        }
//    };
//})
///**
// * Needed to transclude stuff into ng-repeat the way we need to.
// * From: https://github.com/angular/angular.js/issues/7874#issuecomment-47647528
// */
//.directive('inject', function() {
//    return {
//        link: function($scope, $element, $attrs, controller, $transclude) {
//            if (!$transclude) {
//                throw new Error(
//                    'Illegal use of ngTransclude directive in the template! ' +
//                    'No parent directive that requires a transclusion found. '
//                );
//            }
//            // Normally using ng-transclude this is: $scope.$parent.$new();
//            // But then one wouldn't have access to scopes that get created on
//            // the same tag (e.g. when using ng-controller or ng-repeat on the
//            // same level)
//            var innerScope = $scope.$new();

//            // The first argument is optional (transclusion scope),
//            // second is the 'clone attack function' where
//            // clone is the freshly compiled elemen of the wrapped (transcluded)
//            // content which is bound to the transclusion scope `scope` that was
//            // created for it.
//            //
//            // $transclude will return the compiled and linked transcluded
//            // element.
//            $transclude(innerScope, function(clone, scope) { // scope is === innerScope
//                // clone is the compiled html of the wrapped content
//                // The following is basically the same that ngTransclude's
//                // transclude function does.
//                $element.empty();
//                $element.append(clone);
//                $element.on('$destroy', function() {
//                    innerScope.$destroy();
//                });
//            });
//        }
//    };
//});
