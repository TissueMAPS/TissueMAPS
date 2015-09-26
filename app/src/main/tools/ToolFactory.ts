class ToolFactory {
    static $inject = ['$', '$http', '$window', '$rootScope'];
    constructor(private $: JQueryStatic,
                private $http: ng.IHttpService,
                private $window: Window,
                private $rootScope: ng.IRootScopeService) {}

    create(viewport: Viewport,
           id: string,
           name: string,
           description: string,
           template: string,
           icon: string,
           defaultWindowHeight: number,
           defaultWindowWidth: number) {

        return new Tool(
            this.$,
            this.$http,
            this.$window,
            this.$rootScope,
            viewport,
            id,
            name,
            description,
            template,
            icon,
            defaultWindowHeight,
            defaultWindowWidth
        );
   }
}

angular.module('tmaps.main.tools').service('toolFactory', ToolFactory);
