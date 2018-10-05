// Copyright (C) 2016-2018 University of Zurich.
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
.controller('MultiSelectionBoxCtrl', ['$scope', 'uiState', function($scope, uiState) {
    var self = this;

    var tabs = [];

    this.filterProperties = this.filterProperties || {};

    this.removeTab = function(tab) {
        var ind = tabs.indexOf(tab);
        if (ind > -1) {
            tabs.splice(ind, 1);
        }
    };

    this.getTabs = function() {
        return tabs;
    };

    /**
     * Function with which new tabs can register themselves when their
     * constructor is called.
     */
    this.addTab = function(tab) {
        tabs.push(tab);
    };


    /**
     * Since the instance is in scope for the content of this directive,
     * this method can be called by any controller (for example to apply a
     * function to all selected items, whatever they may be).
     */
    this.getSelectedItems = function() {
        return _.chain(tabs)
                .filter(function(t) { return t.isSelected; })
                .map(function(t) { return t.getItem(); })
                .value();
    };

    this.hasSelectedItems = function() {
        return this.getSelectedItems().length > 0;
    };


    /**
     * Check if the item should really be selected.
     *
     * This depends on whether the SHIFT key is pressed.
     * Also, if for example multiple layers are selected, but the shift key
     * isn't held anymore, then all other layers should be deselected.
     * This behavior should be similar to how other applications handle
     * multi-selection.
     */
    this.checkIfShouldSelect = function(tab) {
        var nSelected = self.getSelectedItems().length;
        var alreadySelected = tab.isSelected;
        var othersSelected = alreadySelected && nSelected >= 2 ||
                             !alreadySelected && nSelected >= 1;
        var shiftPressed = uiState.pressedKeys.shift;

        if (!shiftPressed) {
            // If shift is not pressed and other items are selected as well
            if (othersSelected) {
                // ...deselect the other items, but keep this one selected.
                _(tabs).each(function(t) {
                    if (t !== tab) {
                        t.isSelected = false;
                    }
                });
                tab.isSelected = true;
            } else {
                tab.isSelected = !tab.isSelected;
            }
        } else {
            // When shift is pressed, always toggle the selection.
            tab.isSelected = !tab.isSelected;
        }
    };
}]);
