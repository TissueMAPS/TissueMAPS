class SVMTool extends Tool {
    constructor($: JQueryStatic,
                $http: ng.IHttpService,
                $window: Window,
                $rootScope: ng.IRootScopeService,
                appInstance: AppInstance) {
        super(
            $, $http, $window, $rootScope,
            appInstance,
            'SVM',
            'SVM Classifier',
            'Classify cells using a Support Vector Machine',
            '/templates/tools/modules/SVM/svm.html',
            'SVM',
            1025,
            450,
            new EchoResultHandler()
          )
    }
}
