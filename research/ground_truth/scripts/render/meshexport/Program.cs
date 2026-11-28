// Local research tool (never committed with game data): the model of a character, as vertices and triangles.
// Usage: meshexport <chr .chrbnd.dcx> <out dir>
using System.Globalization;
using SoulsFormats;

var bnd = BND4.Read(args[0]);
var outDir = Directory.CreateDirectory(args[1]).FullName;
foreach (var f in bnd.Files) Console.WriteLine($"  {Path.GetFileName(f.Name)} {f.Bytes.Length}");
var inv = CultureInfo.InvariantCulture;
foreach (var f in bnd.Files.Where(f => f.Name.ToLower().EndsWith(".flver")))
{
    var flver = FLVER2.Read(f.Bytes);
    var stem = Path.GetFileNameWithoutExtension(f.Name);
    var verts = new List<string> { "mesh,x,y,z,nx,ny,nz" };
    var tris = new List<string> { "mesh,a,b,c" };
    int offset = 0;
    for (int m = 0; m < flver.Meshes.Count; m++)
    {
        var mesh = flver.Meshes[m];
        foreach (var v in mesh.Vertices)
            verts.Add(string.Format(inv, "{0},{1:F4},{2:F4},{3:F4},{4:F3},{5:F3},{6:F3}", m, v.Position.X, v.Position.Y, v.Position.Z, v.Normal.X, v.Normal.Y, v.Normal.Z));
        var fs = mesh.FaceSets.OrderBy(s => (int)s.Flags).First();
        var idx = fs.Triangulate(mesh.Vertices.Count < ushort.MaxValue);
        for (int i = 0; i + 2 < idx.Count; i += 3)
            tris.Add($"{m},{idx[i] + offset},{idx[i + 1] + offset},{idx[i + 2] + offset}");
        Console.WriteLine($"{stem} mesh {m}: {mesh.Vertices.Count} vertices, {idx.Count / 3} triangles, material {flver.Materials[mesh.MaterialIndex].Name}");
        offset += mesh.Vertices.Count;
    }
    File.WriteAllLines(Path.Combine(outDir, $"{stem}_verts.csv"), verts);
    File.WriteAllLines(Path.Combine(outDir, $"{stem}_tris.csv"), tris);
    Console.WriteLine($"{stem}: {flver.Meshes.Count} meshes, {flver.Bones.Count} bones");
}
