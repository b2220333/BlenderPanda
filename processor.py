import ctypes
import math
import pprint


from OpenGL.GL import *
import panda3d.core as p3d


if "converter" in locals():
    import imp
    imp.reload(converter)
else:
    from . import converter


class PandaProcessor:
    def __init__(self, buffer):
        self.buffer = buffer

        self.engine = p3d.GraphicsEngine()

        gps = p3d.GraphicsPipeSelection.get_global_ptr()
        self.pipe = gps.make_module_pipe('pandagl')

        self.win = None
        self.view_region = None
        self.view_lens = p3d.MatrixLens()
        self.view_camera = p3d.NodePath(p3d.Camera('view'))
        self.view_camera.node().set_lens(self.view_lens)
        self.view_camera.node().set_active(True)

        self.bg = p3d.LVector4(0.0, 0.0, 0.0, 1.0)

        self.converter = converter.Converter()
        self.view_camera.reparent_to(self.converter.scene_root)
        self.view_camera.node().set_scene(self.converter.scene_root)

    def _make_offscreen(self, sx, sy):
        fbprops = p3d.FrameBufferProperties(p3d.FrameBufferProperties.get_default())
        fbprops.set_srgb_color(True)
        fbprops.set_alpha_bits(0)
        wp = p3d.WindowProperties.size(sx, sy)
        flags = p3d.GraphicsPipe.BF_require_callback_window
        self.win = self.engine.make_output(self.pipe, 'viewport', 0, fbprops, wp, flags)
        self.win.disable_clears()

        def render_cb(cbdata):
            cbdata.upcall()
            cbdata.set_render_flag(True)
        self.win.set_render_callback(p3d.PythonCallbackObject(render_cb))

        dr = self.win.make_mono_display_region()
        dr.set_camera(self.view_camera)
        dr.set_active(True)
        dr.set_clear_color_active(True)
        dr.set_clear_color(self.bg)
        dr.set_clear_depth(1.0)
        dr.set_clear_depth_active(True)
        self.view_region = dr

    def process_data(self, data):
        '''Accept converted data to be consumed by the processor'''
        pprint.pprint(data)
        self.converter.update(data)
        bg = self.converter.background_color
        self.bg = p3d.LVector4(bg[0], bg[1], bg[2], 1)
        self.view_region.set_clear_color(self.bg)

        #self.converter.scene_root.ls()

    def fix_gl_state(self):
        '''Issue any GL calls needed to make Panda3D happy'''
        glEnable(GL_DEPTH_TEST)

    def render(self, context):
        window = context.window
        region = context.region
        view = context.region_data

        # Calculate dimensions of the display region.
        pixel_scale = p3d.LVecBase2(1.0 / window.width, 1.0 / window.height)

        dimensions = p3d.LVecBase4(region.x, region.x + region.width,
                               region.y, region.y + region.height)
        dimensions.x *= pixel_scale.x
        dimensions.y *= pixel_scale.x
        dimensions.z *= pixel_scale.y
        dimensions.w *= pixel_scale.y
        
        if self.win is None:
            self._make_offscreen(window.width, window.height)

        self.view_region.set_dimensions(dimensions)

        # Save GL State
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        glPushClientAttrib(~0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()

        try:
            # update window
            wp = p3d.WindowProperties()
            wp.set_origin(window.x, window.y)
            wp.set_size(window.width, window.height)
            self.win.request_properties(wp)
            self.engine.open_windows()

            # update camera
            proj_mat = p3d.LMatrix4()
            for i, v in enumerate(view.perspective_matrix):
                proj_mat.set_col(i, p3d.LVecBase4(*v))
            self.view_lens.set_user_mat(proj_mat)
            self.view_lens.set_view_mat(p3d.LMatrix4.ident_mat())

            #draw
            self.fix_gl_state()
            self.engine.render_frame()
        finally:
            # Restore GL State
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()

            glPopClientAttrib()
            glPopAttrib()

    def update(self, timestep):
        '''Advance the processor by the timestep and update the viewport image'''
        return
