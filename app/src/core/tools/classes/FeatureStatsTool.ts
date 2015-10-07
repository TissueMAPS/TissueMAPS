class FeatureStatsTool extends Tool {
    constructor($: JQueryStatic,
                $http: ng.IHttpService,
                $window: Window,
                $rootScope: ng.IRootScopeService,
                appInstance: AppInstance) {
        super(
            $, $http, $window, $rootScope,
            appInstance,
            'FeatureStats',
            'Feature Statistics',
            'Compute some basic statistics',
            '/templates/tools/modules/featurestats/feature-stats.html',
            '<i class=\"fa fa-bar-chart\"></i>',
            850,
            600,
            new EchoResultHandler()
          )
    }
}
