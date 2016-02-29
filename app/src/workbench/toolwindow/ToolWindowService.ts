class ToolWindowService {

    createWindow()  {
        var $http = $injector.get<ng.IHttpService>('$http');

        var templateUrl = '/src/view/toolwindow/tool-window.html';

        $http.get(templateUrl).then((resp) {
            var template = resp.data;

            // TODO: Change to viewportScope.$new()
            var newScope = this._$rootScope.$new({
                tool: tool
            });

            var ctrl = $injector.get<any>('$controller')('ToolWindowCtrl', {
                '$scope': newScope,
                '$rootScope': $injector.get('$rootScope')
            });

            // Compile the element (expand directives)
            var elem = angular.element(template);
            var linkFunc = $injector.get<ng.ICompileService>('$compile')(elem);
            // Link to scope
            var windowElem = linkFunc(newScope);
            // TODO: Append to DOM of viewport
            // $injector.get<ng.IDocumentService>('$document').find('#viewports').append(viewportElem);
        });

    }

}
