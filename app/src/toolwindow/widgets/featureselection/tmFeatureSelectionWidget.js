angular.module('tmaps.toolwindow')
/**
 * A directive with which features can be selected.
 *
 * Example usage:
 *
 *  <tm-feature-selection-widget
 *    experiment-id="1"
 *    on-change="selection = selectedFeatures"/>
 *
 *  experiment-id should be the database if of the experiment for which
 *  the features should be fetched.
 *  onChange is an expression whose right-hand side can contain the variable
 *  'selectedFeatures'. This variable corresponds to the features which are
 *  marked as selected.
 *
 *  If the directive is used with the optional attribute
 *  'single-selection="true"', then this variable is still a list, although
 *  its length will be 0 or 1.
 */
.directive('tmFeatureSelectionWidget', function() {
    return {
        restrict: 'E',
        scope: {
            singleSelection: '=',
            showRange: '=',
            experimentId: '=',
            onChange: '&'
        },
        bindToController: true,
        templateUrl: '/templates/tools/widgets/tm-feature-selection-widget.html',
        controller: ['$http', 'tmapsProxy', '$scope',
                     function($http, tmapsProxy, $scope) {

            var self = this;

            this.isSingleSelection =
                angular.isDefined(this.singleSelection) && this.singleSelection;
            this.isMultiSelection = !this.isSingleSelection;

            var expId;

            if (!angular.isDefined(this.experimentId)) {
                expId = tmapsProxy.viewport.experiment.id;
            } else {
                expId = this.experimentId;
            }

            tmapsProxy.viewport.experiment.features
            .then(function(feats) {
                self.features = feats;
                $scope.$digest();
            });

            this.toggleSelection = function(feat) {

                if (self.singleSelection) {
                    _(self.features).each(function(f) {
                        if (f != feat) {
                            f.selected = false;
                        }
                    });
                }
                feat.selected = !feat.selected;

                // Extract only those values that are of interest to
                // the user of this directive.
                // Also, we need to recalculate the original values to which
                // the slider range corresponds.
                var selectedFeatures = _.chain(self.features)
                     .filter(function(f) {
                        return f.selected;
                      })
                     .map(function(f) {
                        var feat = { name: f.name };
                        if (self.showRange) {
                            feat.range = [f.normRange[0] / f.fac, f.normRange[1] / f.fac];
                        }
                        return feat;
                      })
                     .value();

                self.onChange({
                    selectedFeatures: selectedFeatures
                });
            };

            this.setAll = function(val) {
                _(self.features).each(function(f) {
                    f.selected  = val;
                });
            };
        }],
        controllerAs: 'ctrl'
    };
})
.controller('FeatureTabCtrl', ['$scope', function($scope) {

    // Compute a normalized range that has width 100 so that ui.slider
    // won't be buggy. These ranges need to be recalculated when updating
    // the client's onChange expression.
    // $scope.feat.fac = 100 / ($scope.feat.max - $scope.feat.min);
    // $scope.feat.normRange = [
    //     $scope.feat.min * $scope.feat.fac,
    //     $scope.feat.max * $scope.feat.fac
    // ];

    // $scope.normRangeMax = $scope.feat.max * $scope.feat.fac;
    // $scope.normRangeMin = $scope.feat.min * $scope.feat.fac;

}]);
