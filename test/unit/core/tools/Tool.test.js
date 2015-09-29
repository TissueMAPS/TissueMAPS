describe('In Tool', function() {
    // Load the module of ObjectLayer and its dependencies
    beforeEach(module('tmaps.main.tools'));

    var tool;
    var toolId = 'SomeTool';
    var toolName = 'SomeTool';
    var toolDescription = 'Some test tool';
    var toolTemplate = '<div>test</div>';
    var toolIcon = ':)';
    var defaultWindowWidth = 800;
    var defaultWindowHeight = 600;

    // Injected services and factories
    var toolFactory;

    beforeEach(inject(function(_toolFactory_) {
        // Assign to variables
        toolFactory = _toolFactory_;
    }));


    beforeEach(function() {
        tool = toolFactory.create(
            {},
            toolId,
            toolName,
            toolDescription,
            toolTemplate,
            toolIcon,
            defaultWindowHeight,
            defaultWindowWidth
        );
    });

    describe('the function getIdSlug', function() {
        function createToolGivenId(id) {
            var t = toolFactory.create(
                {},
                id,
                toolName,
                toolDescription,
                toolTemplate,
                toolIcon,
                defaultWindowHeight,
                defaultWindowWidth
            );
            return t;
        }

        it('makes the tool\'s id URL-compatible', function() {
            var t = createToolGivenId('SomeId');
            expect(t.getIdSlug()).toEqual('someid');

            var t = createToolGivenId('SomeId99');
            expect(t.getIdSlug()).toEqual('someid99');

            var t = createToolGivenId('Some-Id');
            expect(t.getIdSlug()).toEqual('some-id');

            var t = createToolGivenId('---SOME__ID--');
            expect(t.getIdSlug()).toEqual('some-id');

            var t = createToolGivenId('**(Some)(id__)');
            expect(t.getIdSlug()).toEqual('some-id');

            var t = createToolGivenId('so me-id');
            expect(t.getIdSlug()).toEqual('so-me-id');
        });
    });

    describe('the function createNewWindow', function() {
        it('should create a tool window on the server');
        it('should open a new window');
    });

    describe('the function removeToolWindow', function() {
        it('should delete the window server-side');
        it('should close the window client-side');
    });

    describe('an open toolwindow', function() {
        it('should display the tools template');
        it('should request the tools remote deletion upon closing the window');
    });

});

