// http://angular.github.io/protractor/#/api

describe('[e2e] Routes:', function() {

    describe('the welcome page', function() {

        beforeEach(function() {
	          browser.get('/');
        });

        it('should be loaded when navigating to "/"', function() {
            expect(browser.getLocationAbsUrl()).toMatch('/welcome');
        });

        it('should display a large welcome message', function() {
            expect($('.jumbotron h1').getText()).toMatch(/Welcome/);
        });

        describe('should have a login form', function() {
            // Why are there two login forms on that page?!
            var loginForm = $$('form.tm-inline-login-form').get(0);
            var inputElems = loginForm.$$('input');
            var username = inputElems.get(0);
            var password = inputElems.get(1);
            var submitButton = loginForm.$('button');
            var userLinks = $$('.user-indicator a');

            it('that, when clicked, displays the user\'s name', function() {
                username.sendKeys('testuser');
                password.sendKeys('123');
                submitButton.click();

                // After login, the name of the just logged-in user should be displayed
                expect(userLinks.get(0).getText()).toEqual('testuser');
                // Login form should be hidden
                expect(loginForm.isDisplayed()).not.toBeTruthy();
            });

            it('that, when clicked, can be used to go to the userpanel', function() {
                // The browser gets reloaded (because of the beforeEach),
                // but since the user info is stored on sessionStorage
                // the user will stay logged in!
                expect(userLinks.get(0).getAttribute('ui-sref')).toEqual('viewport.userpanel');
            });

            it('has a working logout button', function() {
                // Click the logout link
                userLinks.get(1).click();
                // Login form should be visible again
                expect(loginForm.isDisplayed()).toBeTruthy();
            });

        });

    });

});
