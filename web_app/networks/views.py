# Create your views here.
#from django.shortcuts import get_object_or_404, render_to_response
#from django.http import HttpResponseRedirect, HttpResponse
#from django.core.urlresolvers import reverse
#from django.template import RequestContext 
from web_app.networks.models import Gene

from django.template import RequestContext
from django.http import HttpResponse
from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render_to_response
from django.db.models import Q
from web_app.networks.models import *
from web_app.networks.functions import functional_systems
import networkx as nx
import re
import sys, traceback


class Object(object):
    pass

# I renamed this to make a gene page
def analysis_gene(request):
    #return render_to_response('analysis/gene.html')
    return render_to_response('analysis/gene.html', {}, context_instance=RequestContext(request))


def networks(request):
    networks = Network.objects.all()
    return render_to_response('networks.html', locals())

def network(request, network_id=None):
    network = Network.objects.get(id=network_id)
    biclusters = network.bicluster_set.all()
    return render_to_response('network.html', locals())

def network_cytoscape_web_test(request):
    network = Object()
    network.name = "Test Network"
    network.bicluster_ids = [2,152,299]
    return render_to_response('network_cytoscape_web.html', locals())

def network_cytoscape_web(request):
    network = Object()
    network.name = "Test Network"
    if request.GET.has_key('biclusters'):
        network.bicluster_ids = re.split( r'[\s,;]+', request.GET['biclusters'] )
    return render_to_response('network_cytoscape_web.html', locals())

def network_as_graphml(request):
    if request.GET.has_key('biclusters'):
        bicluster_ids = re.split( r'[\s,;]+', request.GET['biclusters'] )
    biclusters = Bicluster.objects.filter(id__in=bicluster_ids)

    graph = nx.Graph()

    # compile set of genes in all requested biclusters
    genes = set()
    influences = set()
    for b in biclusters:
        genes.update(b.genes.all())
        for influence in b.influences.all():
            influences.add(influence)
            if influence.is_combiner():
                parts = influence.get_parts()
                influences.update(parts)
                for part in parts:
                    graph.add_edge("inf:%d" % (part.id,), "inf:%d" % (influence.id,))
        print "influences = %d" % (len(influences),)
        print influences

    # build networkx graph
    for gene in genes:
        graph.add_node(gene, {'type':'gene', 'name':gene.display_name()})
    for inf in influences:
        graph.add_node("inf:%d" % (inf.id,), {'type':'regulator', 'name':inf.name})
    for bicluster in biclusters:
        graph.add_node("bicluster:%d" %(bicluster.id,), {'type':'bicluster', 'name':str(bicluster)})
        for gene in bicluster.genes.all():
            graph.add_edge("bicluster:%d" %(bicluster.id,), gene)
        for inf in bicluster.influences.all():
            graph.add_edge("bicluster:%d" %(bicluster.id,), "inf:%d" % (inf.id,))
            print ">>> " + str(inf)
        for motif in bicluster.motif_set.all():
            graph.add_node("motif:%d" % (motif.id,), {'type':'motif', 'consensus':motif.consensus(), 'e_value':motif.e_value, 'name':"motif:%d" % (motif.id,)})
            graph.add_edge("bicluster:%d" %(bicluster.id,), "motif:%d" % (motif.id,))

    # write graphml to response
    writer = nx.readwrite.graphml.GraphMLWriter(encoding='utf-8',prettyprint=True)
    writer.add_graph_element(graph)
    response = HttpResponse(content_type='application/xml')
    writer.dump(response)

    return response

def species(request, species=None, species_id=None):
    try:
        if species:
            try:
                species_id = int(species)
                species = Species.objects.get(id=species_id)
            except ValueError:
                species = Species.objects.get(Q(name=species) | Q(short_name=species))
                # try aliases, too?
        elif species_id:
            species = Species.objects.get(id=species_id)
        elif request.GET.has_key('id'):
            species_id = request.GET['id']
            species = Species.objects.get(id=species_id)
        else:
            species = Species.objects.all()
            return render_to_response('species_list.html', locals())
        gene_count = species.gene_set.count()
        transcription_factors = species.gene_set.filter(transcription_factor=True)
        chromosomes = species.chromosome_set.all()
        return render_to_response('species.html', locals())
    except (ObjectDoesNotExist, AttributeError):
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_stack()
        traceback.print_exception(exc_type, exc_value, exc_traceback,
                              limit=2, file=sys.stdout)
        if species:
            raise Http404("Couldn't find species: " + str(species))
        elif species_id:
            raise Http404("Couldn't find species with id=" + species_id)
        else:
            raise Http404("No species specified.")

def genes(request, species=None, species_id=None):
    try:
        if species:
            try:
                species_id = int(species)
                species = Species.objects.get(id=species_id)
            except ValueError:
                species = Species.objects.get(Q(name=species) | Q(short_name=species))
                # try aliases, too?
        elif request.GET.has_key('id'):
                species_id = request.GET['id']
                species = Species.objects.get(id=species_id)
        else:
            gene_count = Gene.objects.count()
            species_count = Species.objects.count()
            return render_to_response('genes_empty.html', locals())
        
        # handle filters or just get all genes for the species
        if request.GET.has_key('filter'):
            filter = request.GET['filter']
            if filter == 'tf':
                genes = species.gene_set.filter(transcription_factor=True)
        else:
            genes = species.gene_set.all()
        
        gene_count = len(genes)
        return render_to_response('genes.html', locals())
    except (ObjectDoesNotExist, AttributeError):
        if species:
            raise Http404("Couldn't find genes for species: " + species)
        elif species_id:
            raise Http404("Couldn't find genes for species with id=" + species_id)
        else:
            raise Http404("No species specified.")

def gene(request, gene=None):
    if gene:
        try:
            gene_id = int(gene)
            gene = Gene.objects.get(id=gene_id)
        except ValueError:
            gene = Gene.objects.get(name=gene)
    elif request.GET.has_key('id'):
        gene_id = request.GET['id']
        gene = Gene.objects.get(id=gene_id)
    else:
        gene_count = Gene.objects.count()
        species_count = Species.objects.count()
        return render_to_response('genes_empty.html', locals())
    
    # compile functions into groups by functional system
    systems = []
    for key, functions in gene.functions_by_type().items():
        system = {}
        system['name'] = functional_systems[key].display_name
        system['functions'] = [ "(<a href=\"%s\">%s</a>) %s" % (function.link_to_term(), function.native_id, function.name,) \
                                for function in functions ]
        systems.append(system)  
    
    # if the gene is a transcription factor, how many biclusters does it regulate?
    count_regulated_biclusters = gene.count_regulated_biclusters(1)
    
    if request.GET.has_key('format'):
        format = request.GET['format']
        if format == 'html':
            return render_to_response('gene_snippet.html', locals())
    
    return render_to_response('gene.html', locals())

def bicluster(request, bicluster_id=None):
    bicluster = Bicluster.objects.get(id=bicluster_id)
    genes = bicluster.genes.all()
    gene_count = len(genes)
    influences = bicluster.influences.all()
    conditions = bicluster.conditions.all()
    
    if request.GET.has_key('format'):
        format = request.GET['format']
        if format == 'html':
            return render_to_response('bicluster_snippet.html', locals())

    return render_to_response('bicluster.html', locals())

def regulated_by(request, regulator=None):
    gene = Gene.objects.get(name=regulator)
    network = Network.objects.get(id=1)
    biclusters = gene.regulated_biclusters(network)
    bicluster_ids = [bicluster.id for bicluster in biclusters]
    return render_to_response('biclusters.html', locals())

def regulator(request, regulator=None):
    influence = Influence.objects.get(name=regulator)
    parts = influence.parts.all()
    return render_to_response('influence_snippet.html', locals())

def functions(request, type):
    system = None
    if type in functional_systems:
        system = functional_systems[type]
    return render_to_response('functions.html', locals())

def function(request, name):
    function = None
    if re.match("\d+", name):
        function = Function.objects.get(id=name)
    if function is None:
        function = Function.objects.get(native_id=name)
    if function is None:
        function = Function.objects.get(name=name)
    return render_to_response('function.html', locals())

def motif(request, motif_id=None):
    motif = Motif.objects.get(id=motif_id)
    return render_to_response('motif_snippet.html', locals())

