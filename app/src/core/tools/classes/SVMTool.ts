class SVMTool extends ClassificationTool {
    constructor(appInstance: AppInstance) {
        super(
            appInstance,
            'SVM',
            'SVM Classifier',
            'Classify cells using a Support Vector Machine',
            '/templates/tools/modules/SVM/svm.html',
            'SVM',
            1025,
            450
          )
    }
}
