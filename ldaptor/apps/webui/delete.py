from zope.interface import implements
from ldaptor.protocols.ldap import ldapsyntax, distinguishedname
from ldaptor.apps.webui.uriquote import uriUnquote
from ldaptor.apps.webui.i18n import _
from ldaptor.apps.webui import i18n
from ldaptor import weave

import os
from nevow import rend, inevow, loaders, url, tags
from formless import annotate, webform, iformless

class ErrorWrapper:
    def __init__(self, value):
        self.value = value

class ConfirmDelete(rend.Page):
    docFactory = loaders.xmlfile(
        'delete.xhtml',
        templateDir=os.path.split(os.path.abspath(__file__))[0])

    def __init__(self, dn):
        super(ConfirmDelete, self).__init__()
        self.dn = dn

    def getBindingNames(self, ctx):
        return ['delete']

    def bind_delete(self, ctx):
        return annotate.MethodBinding(
            'delete',
            annotate.Method(arguments=[
            annotate.Argument('ctx', annotate.Context()),
            ],
                            label=_('Confirm delete')),
            action=_('Delete'))

    def data_css(self, ctx, data):
        u = (url.URL.fromContext(ctx).clear().parentdir().parentdir()
             .child('form.css'))
        return [ u ]

    def render_css_item(self, context, data):
        context.fillSlots('url', data)
        return context.tag

    def delete(self, ctx):
        request = inevow.IRequest(ctx)
        user = request.getSession().getLoggedInRoot().loggedIn
        e=ldapsyntax.LDAPEntry(client=user.client,
                               dn=self.dn)
        d=e.delete()
        d.addCallbacks(
            callback=lambda dummy: _("Success."),
            errback=lambda fail: _("Failed: %s.")
            % fail.getErrorMessage())
        def _redirect(r):
            u = url.URL.fromContext(ctx)
            u = u.child('deleted')
            request.setComponent(iformless.IRedirectAfterPost, u)
            return r
        d.addBoth(_redirect)
        return d

    def child_deleted(self, request):
        return Deleted(self.dn)

    def data_entry(self, context, data):
        user = context.locate(inevow.ISession).getLoggedInRoot().loggedIn
        assert user

        entry = ldapsyntax.LDAPEntry(client=user.client, dn=self.dn)
        d = entry.fetch()
        d.addErrback(ErrorWrapper)
        return d

    def render_error_or_pass(self, context, data):
        if isinstance(data, ErrorWrapper):
            return context.tag.clear() \
                   [ tags.strong(style="color: red;") \
                     [ _('An error occurred: '),
                       data.value.getErrorMessage(),
                       ]
                     ]
        else:
            return context.tag

    def data_dn(self, context, data):
        return self.dn

    def render_form(self, context, data):
        return webform.renderForms()

    def render_passthrough(self, context, data):
        return context.tag.clear()[data]

    def data_header(self, ctx, data):
        u=url.URL.fromContext(ctx)
        u=u.parentdir().parentdir()
        l=[]
        l.append(tags.a(href=u.sibling("search"))[_("Search")])
        l.append(tags.a(href=u.sibling("add"))[_("add new entry")])
        l.append(tags.a(href=u.sibling("edit").child(str(self.dn)))[_("edit")])
        return l

    def render_keyvalue(self, context, data):
        return weave.keyvalue(context, data)

    def render_keyvalue_item(self, context, data):
        return weave.keyvalue_item(context, data)

    render_i18n = i18n.render()

class Deleted(rend.Page):
    docFactory = loaders.xmlfile(
        'delete-done.xhtml',
        templateDir=os.path.split(os.path.abspath(__file__))[0])

    def __init__(self, dn):
        super(Deleted, self).__init__()
        self.dn = dn

    def data_dn(self, context, data):
        return self.dn

    def data_header(self, ctx, data):
        u=url.URL.fromContext(ctx)
        u=u.parentdir().parentdir()
        l=[]
        l.append(tags.a(href=u.sibling("search"))[_("Search")])
        l.append(tags.a(href=u.sibling("add"))[_("add new entry")])
        return l

    def render_passthrough(self, context, data):
        return context.tag.clear()[data]

    def data_status(self, context, data):
        try:
            return context.locate(inevow.IStatusMessage)
        except KeyError:
            return _('Internal error, no status to display.')

    render_i18n = i18n.render()

    def render_data(self, ctx, data):
        return ctx.tag.clear()[data]

class GetDN(rend.Page):
    addSlash = True

    docFactory = loaders.xmlfile(
        'delete-nodn.xhtml',
        templateDir=os.path.split(os.path.abspath(__file__))[0])

    def render_url(self, context, data):
        u = url.URL.fromContext(context)
        return context.tag(href=u.parentdir().child('search'))

    def childFactory(self, context, name):
        unquoted=uriUnquote(name)
        try:
            dn = distinguishedname.DistinguishedName(stringValue=unquoted)
        except distinguishedname.InvalidRelativeDistinguishedName, e:
            # TODO There's no way to throw a FormException at this stage.
            return None
        r=ConfirmDelete(dn=dn)
        return r

    render_i18n = i18n.render()

def getResource():
    return GetDN()
