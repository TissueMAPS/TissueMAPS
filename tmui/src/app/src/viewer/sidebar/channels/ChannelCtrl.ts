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
.controller('ChannelCtrl', ['$scope', function($scope) {
    var self = this;
    this.inRenamingMode = false;

    this.renameChannel = function(channel) {
        var dao = new ChannelDAO(channel._$stateParams.experimentid);
        var newName = channel.name.replace(/[^-A-Z0-9]+/ig, "_");
        dao.update(channel.id, {
            name: newName
        }).then(() => {
            // Replace all special characters by underscore
            channel.name = newName;
        }, () => {
            channel.name = this._origName;
        });
    }

    this.toggleRenamingMode = function() {
        this.inRenamingMode = !this.inRenamingMode;
    }

    // Call the exposed method of the boxCtrl
    function getSelectedChannels() {
        return $scope.selectionBox.getSelectedItems();
    }

    this.getBrightnessFormatted = function(channel) {
        return Math.floor(channel.brightness * 100);
    };

    this.getOpacityFormatted = function(channel) {
        return Math.floor(channel.opacity * 100);
    };

    this.color = {
        RED:   Color.RED,
        GREEN: Color.GREEN,
        BLUE:  Color.BLUE
    };

    this.setColor = function(channel, color) {
        if (channel.color.equals(color)) {
            // Same color was selected, unselect it by setting null.
            channel.color = null;
        } else {
            channel.color = color;
        }
    };

    this.isRed = function(channel) {
        return channel.color.equals(this.color.RED);
    };
    this.isGreen = function(channel) {
        return channel.color.equals(this.color.GREEN);
    };
    this.isBlue = function(channel) {
        return channel.color.equals(this.color.BLUE);
    };

    // Since two-way data binding isn't possible on the channel properties
    // with a ui-slider, the values are watched manually and the input model is
    // changed so that the slider accurately reflects the model state.
    // Note that the values stored on the channel object doesn't correspond to the
    // slider intervals, therefore they have to be readjusted (e.g. by
    // multiplying times 100 so that 0.5 * 100 = 50).

    // Initialize the input models
    this._origName = $scope.channel.name;
    this.maxInput = $scope.channel.max * 255;
    this.minInput = $scope.channel.min * 255;
    this.brightnessInput = $scope.channel.brightness * 100;
    this.opacityInput = $scope.channel.opacity * 100;

    // Setup watches
    // TODO: the slider for MAXIMUM doesn't work correctly. Isn't it set up properly?
    $scope.$watch('channel.max', function(newVal) {
        self.maxInput = newVal * 255;
    });

    $scope.$watch('channel.min', function(newVal) {
        self.minInput = newVal * 255;
    });

    $scope.$watch('channel.brightness', function(newVal) {
        self.brightnessInput = newVal * 100;
    });

    $scope.$watch('channel.opacity', function(newVal) {
        self.opacity = newVal * 100;
    });

    this.setDefaultSettings = function(channel) {
        this.setChannelMin(channel, 0);
        this.setChannelMax(channel, 1);
        this.setChannelBrightness(channel, 0);
        this.setChannelOpacity(channel, 1);
    };

    /**
     * The following methods set the channel property min to `val` for channel
     * and all other selected channels if there are such.
     */
    this.setChannelMin = function(channel, val) {
        if (_(getSelectedChannels()).contains(channel)) {
            getSelectedChannels().forEach(function(l) {
                l.min = val;
            });
        } else {
            channel.min = val;
        }
    };

    this.getActualChannelMin = function(channel) {
        return Math.round(channel.min * (channel.maxIntensity - channel.minIntensity) + channel.minIntensity);
    };

    this.setChannelMax = function(channel, val) {
        if (_(getSelectedChannels()).contains(channel)) {
            getSelectedChannels().forEach(function(l) {
                l.max = val;
            });
        } else {
            channel.max = val;
        }
    };

    this.getActualChannelMax = function(channel) {
        return Math.round(channel.max * (channel.maxIntensity - channel.minIntensity) + channel.minIntensity);
    };

    this.setChannelBrightness = function(channel, val) {
        if (_(getSelectedChannels()).contains(channel)) {
            getSelectedChannels().forEach(function(l) {
                l.brightness = val;
            });
        } else {
            channel.brightness = val;
        }
    };

    this.setChannelOpacity = function(channel, val) {
        if (_(getSelectedChannels()).contains(channel)) {
            getSelectedChannels().forEach(function(l) {
                l.opacity = val;
            });
        } else {
            channel.opacity = val;
        }
    };
}]);
