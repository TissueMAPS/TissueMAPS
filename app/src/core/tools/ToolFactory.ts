class ToolFactory {
    static $inject = ['$', '$http', '$window', '$rootScope'];
    constructor(private $: JQueryStatic,
                private $http: ng.IHttpService,
                private $window: Window,
                private $rootScope: ng.IRootScopeService) {}

    create(appInstance: AppInstance,
           className: string) {
        var cls = window[className];
        return new cls(
            this.$,
            this.$http,
            this.$window,
            this.$rootScope,
            appInstance
        );
   }
}

angular.module('tmaps.core').service('toolFactory', ToolFactory);
